#!/usr/bin/env python3
"""每天生成一篇去水印 API 宣传文，并新建一个 GitHub 公开仓库发布。"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
README_PATH = ROOT / "README.md"

SITE = "https://video.zacao.top"
DOCS = "https://video.zacao.top/docs"
BUY = "https://video.zacao.top/buy"
REPO = "https://github.com/luzacao/video-parse-api"
PASSWORD = "zacao"

MUST_MENTION = [
    SITE,
    DOCS,
    BUY,
    REPO,
    PASSWORD,
]

TOPICS = [
    "抖音分享链接怎么一键拿到无水印视频",
    "快手口令 / 短链解析失败时怎么排查",
    "豆包、即梦 AI 视频分享链去水印",
    "小红书图文 / 实况图 image_list 怎么用",
    "视频号、公众号能解析什么、不能解析什么",
    "API Key 购买、限流和错误码怎么向用户解释",
    "parse、parse/v2、detail、video/stream 怎么选",
    "给运营 / 非研发看的 3 分钟上手指南",
    "和「网页复制保存」比，接口批量的优势",
    "直链过期、防盗链、代理播放那些坑",
]

# 仓库名每天换关键词组合，便于 GitHub 搜索收录
REPO_NAME_PATTERNS = [
    "douyin-kuaishou-qushuiyin-api-{date}",
    "doubao-watermark-free-parse-{date}",
    "xiaohongshu-kuaishou-parse-api-{date}",
    "short-video-no-watermark-api-{date}",
    "wechat-channels-qushuiyin-{date}",
    "jimeng-doubao-video-parse-{date}",
    "tiktok-douyin-watermark-api-{date}",
    "video-parse-api-qushuiyin-{date}",
]

REPO_TOPICS = [
    "watermark",
    "douyin",
    "kuaishou",
    "tiktok",
    "api",
    "video",
    "parser",
    "doubao",
]

# 每天换一种写法，避免读者一看就是同一模板
FORMATS = [
    {
        "name": "客服问答体",
        "how": (
            "全文用「问 / 答」至少 5 组。开头一句人话打招呼。"
            "中间穿插一张小表格。结尾用加粗的行动号召。"
        ),
    },
    {
        "name": "三步上手卡片",
        "how": (
            "用「30 秒看懂 → 三步操作 → 复制即用」结构。"
            "步骤用有序列表，必须给一段可复制的 curl。"
            "文中至少两个引用块（> ）放宣传金句。"
        ),
    },
    {
        "name": "避坑清单",
        "how": (
            "标题带「别再踩」或「清单」。正文用 6～8 条 checkbox 风格列表"
            "（- [ ] / - [x]）。每条坑后面立刻写正确做法和体验入口。"
        ),
    },
    {
        "name": "对比测评体",
        "how": (
            "先做「自己下 / 找群里工具 / 用本站 API」三列表格对比，"
            "再写结论。语气像测评博主，但事实以 README 接口为准。"
        ),
    },
    {
        "name": "场景故事体",
        "how": (
            "用一个具体人设开场（如短视频剪辑、电商素材、自媒体二创），"
            "讲他今天遇到的麻烦，再引出本站怎么解决。段落短，可穿插对话。"
        ),
    },
    {
        "name": "发布说明 / Changelog",
        "how": (
            "写成「今日推荐 / 适合谁 / 怎么试」的产品更新稿。"
            "用 ## 今日推荐、## 适合谁、## 怎么试 三个二级标题。"
            "必须有一行大字口号，指向体验地址。"
        ),
    },
    {
        "name": "代码优先",
        "how": (
            "开头 80 字内说明价值，立刻给 Python 完整示例，再给 curl。"
            "代码注释里也要写上体验地址。后半才讲概念。"
        ),
    },
    {
        "name": "表格海报体",
        "how": (
            "至少两张 Markdown 表格：平台能力和入口信息。"
            "少写长段落。结尾用编号 1.2.3. 把网址、密码、购买页再列一遍。"
        ),
    },
]


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def getenv(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def today() -> dt.date:
    return dt.datetime.now(TZ).date()


def pick(items: list, day: dt.date, salt: int = 0):
    return items[(day.toordinal() + salt) % len(items)]


def call_deepseek(prompt: str, temperature: float) -> str:
    api_key = getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("缺少 DEEPSEEK_API_KEY")
    base = getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你在给「短视频去水印 API」写 GitHub 仓库首页 README，读者来自 GitHub 搜索。\n"
                    "只输出完整 Markdown 正文，不要包 ```markdown。\n"
                    "不要编造 README 里没有的接口路径。\n"
                    "这是投放内容：自然、好读、每天换说法，但硬广信息一条都不能少。\n"
                    "标题里尽量带上「去水印」「抖音」或「快手」等检索词，但不要堆砌。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SystemExit(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    msg = (body.get("choices") or [{}])[0].get("message") or {}
    text = (msg.get("content") or "").strip()
    if not text:
        raise SystemExit(f"DeepSeek 返回空内容: {json.dumps(body)[:500]}")
    if text.startswith("```"):
        text = re.sub(r"^```(?:markdown|md)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    return text


def promo_rules() -> str:
    return f"""【硬性宣传规则，缺一条就算失败】
1. 正文里必须出现可点击的 Markdown 链接，且原文精确包含这些 URL（一个字都不能改）：
   - 体验站：[{SITE}]({SITE})
   - 接口文档：[{DOCS}]({DOCS})
   - 购买 Key：[{BUY}]({BUY})
   - GitHub：[{REPO}]({REPO})
2. 必须写清访问密码，原文出现：`{PASSWORD}`（用行内代码包起来）。
3. 必须写清 Base URL 是 {SITE} ，解析接口是 POST `/api/parse`，Header 是 `X-API-Key`。
4. 必须提到：首页可不带 Key 试用，每个 IP 每小时 30 次；正式对接去购买页。
5. 标题或首段 120 字内就要出现体验网址，不要把网址藏到文末才说。
6. 结尾必须有「现在就去试」行动区，再次列出：网址、密码、文档、购买、GitHub。
7. 不要用「某站」「本接口」这种空指代代替网址；每次点名都用完整链接。
8. 可以夸好用、稳定、30+ 平台，但不要编造成功案例数字、价格、和其它竞品的不实对比。
"""


def format_rules(style: dict) -> str:
    return f"""【今日文风，必须遵守】
版式名称：{style['name']}
写法要求：{style['how']}
另外：
- 开场换一种新比喻或新场景，不要用「今天要解决的问题很具体」这种套话。
- 小标题不要天天都是「对接步骤 / 常见坑 / 体验入口」三件套；按今日版式自拟。
- 至少出现一次加粗口号，内容需包含「去水印」和体验域名 video.zacao.top。
"""


def build_prompt(day: dt.date, topic: str, style: dict, api_readme: str) -> str:
    existing = sorted(p.name for p in ARTICLES_DIR.glob("*.md") if p.name != "README.md")
    recent = "、".join(existing[-8:]) if existing else "（暂无）"
    return f"""日期：{day.isoformat()}（北京时间）
今日主题：{topic}

{promo_rules()}

{format_rules(style)}

请写一篇中文宣传+技术短文，约 700～1300 字。服务名可用「短视频去水印 API」或「video.zacao.top 去水印接口」。

已发布文件（避免标题和结构撞车）：{recent}

接口事实以这份 README 为准：

{api_readme[:5000]}
"""


def ensure_promo(body: str) -> str:
    """模型漏写硬广时，文末强制补一块，保证每篇都能带上网址。"""
    missing = [item for item in MUST_MENTION if item not in body]
    if not missing and f"]({SITE})" in body:
        return body
    footer = f"""

---

## 现在就去试

**去水印就用 [{SITE}]({SITE})，访问密码 `{PASSWORD}`。**

| 入口 | 链接 |
| --- | --- |
| 在线体验 | [{SITE}]({SITE}) |
| 访问密码 | `{PASSWORD}` |
| 接口文档 | [{DOCS}]({DOCS}) |
| 购买 Key | [{BUY}]({BUY}) |
| GitHub | [{REPO}]({REPO}) |

首页可不登录 Key 试用（每 IP 每小时 30 次）。批量对接走 `POST {SITE}/api/parse`，Header 带 `X-API-Key`。
"""
    if footer.strip() in body:
        return body
    return body.rstrip() + footer


def write_article(day: dt.date, body: str) -> Path:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTICLES_DIR / f"{day.isoformat()}.md"
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    return path


def rewrite_index(entries: list[dict]) -> None:
    files = sorted(p for p in ARTICLES_DIR.glob("*.md") if p.name != "README.md")
    lines = [
        "# 每日文档",
        "",
        f"每天 06:00（北京时间）自动**新建一个公开仓库**发布。试用：[video.zacao.top]({SITE}) ，密码 `{PASSWORD}`。",
        "",
        "## 每日仓库",
        "",
    ]
    catalog = ARTICLES_DIR / "repos.json"
    history: list[dict] = []
    if catalog.is_file():
        try:
            history = json.loads(catalog.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    by_date = {item.get("date"): item for item in history if item.get("date")}
    for item in entries:
        by_date[item["date"]] = item
    history = [by_date[k] for k in sorted(by_date, reverse=True)]
    catalog.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in history:
        lines.append(f"- [{item['date']}]({item['url']}) `{item['repo']}`")
    lines.extend(["", "## 文稿备份", ""])
    for p in reversed(files):
        title = p.stem
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        lines.append(f"- [{p.stem} · {title}]({p.name})")
    lines.append("")
    (ARTICLES_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def github_api(method: str, path: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "video-parse-daily-publisher",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(f"GitHub {method} {path} -> {exc.code}: {detail}") from exc


def repo_name_for(day: dt.date) -> str:
    stamp = day.strftime("%Y%m%d")
    pattern = pick(REPO_NAME_PATTERNS, day, 5)
    return pattern.format(date=stamp)


def repo_description(day: dt.date, topic: str) -> str:
    return (
        f"{day.isoformat()} 短视频去水印 API · 抖音/快手/豆包/小红书解析 · "
        f"{topic} · {SITE}"
    )[:350]


def ensure_daily_repo(token: str, owner: str, name: str, description: str) -> dict:
    try:
        info = github_api("GET", f"/repos/{owner}/{name}", token)
        print(f"今日仓库已存在，更新 README：{info.get('html_url')}")
        return info
    except RuntimeError as exc:
        if "-> 404:" not in str(exc):
            raise
    info = github_api(
        "POST",
        "/user/repos",
        token,
        {
            "name": name,
            "description": description,
            "homepage": SITE,
            "private": False,
            "has_issues": False,
            "has_projects": False,
            "has_wiki": False,
            "auto_init": False,
        },
    )
    try:
        github_api(
            "PUT",
            f"/repos/{owner}/{name}/topics",
            token,
            {"names": REPO_TOPICS},
        )
    except RuntimeError as exc:
        print(f"设置 topics 失败（可忽略）：{exc}")
    print(f"已新建仓库：{info.get('html_url')}")
    return info


def git_identity_env() -> dict:
    env = os.environ.copy()
    name = getenv("GIT_USER_NAME", "daily-publisher")
    email = getenv("GIT_USER_EMAIL", "daily-publisher@users.noreply.github.com")
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email
    return env


def push_new_repo(token: str, owner: str, name: str, readme: str) -> None:
    git_env = git_identity_env()
    url = f"https://x-access-token:{token}@github.com/{owner}/{name}.git"
    tmp = Path(tempfile.mkdtemp(prefix="daily-repo-"))
    try:
        (tmp / "README.md").write_text(readme.rstrip() + "\n", encoding="utf-8")
        run(["git", "init", "-b", "main"], cwd=tmp, env=git_env, capture_output=True)
        run(["git", "add", "README.md"], cwd=tmp, env=git_env)
        run(
            [
                "git",
                "-c",
                f"user.name={git_env['GIT_AUTHOR_NAME']}",
                "-c",
                f"user.email={git_env['GIT_AUTHOR_EMAIL']}",
                "commit",
                "-m",
                "docs: 发布去水印 API 说明",
            ],
            cwd=tmp,
            env=git_env,
            capture_output=True,
        )
        run(["git", "remote", "add", "origin", url], cwd=tmp, env=git_env)
        run(["git", "push", "-u", "origin", "HEAD:main", "--force"], cwd=tmp, env=git_env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def git_publish_hub(paths: list[Path], message: str) -> None:
    token = getenv("GITHUB_TOKEN")
    repo = getenv("GITHUB_REPO", "luzacao/video-parse-api")
    run(["git", "-C", str(ROOT), "add", "--"] + [str(p) for p in paths])
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    if not status.stdout.strip():
        print("主仓库无文件变更，跳过提交")
        return
    run(
        [
            "git",
            "-C",
            str(ROOT),
            "-c",
            "user.name=" + getenv("GIT_USER_NAME", "daily-publisher"),
            "-c",
            "user.email=" + getenv("GIT_USER_EMAIL", "daily-publisher@users.noreply.github.com"),
            "commit",
            "-m",
            message,
        ]
    )
    if not token:
        raise SystemExit("缺少 GITHUB_TOKEN，无法 push")
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    git_env = git_identity_env()
    run(["git", "-C", str(ROOT), "pull", "--rebase", url, "main"], env=git_env)
    run(["git", "-C", str(ROOT), "push", url, "HEAD:main"], env=git_env)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv(ROOT / ".env")
    token = getenv("GITHUB_TOKEN")
    owner = getenv("GITHUB_OWNER", "luzacao")
    if not token:
        raise SystemExit("缺少 GITHUB_TOKEN")
    day = today()
    topic = pick(TOPICS, day, 0)
    style = pick(FORMATS, day, 3)
    name = repo_name_for(day)
    api_readme = README_PATH.read_text(encoding="utf-8") if README_PATH.is_file() else ""
    print(f"生成 {day.isoformat()} 主题：{topic}", flush=True)
    print(f"今日版式：{style['name']}", flush=True)
    print(f"今日仓库：{owner}/{name}", flush=True)
    body = call_deepseek(build_prompt(day, topic, style, api_readme), temperature=0.95)
    body = ensure_promo(body)
    info = ensure_daily_repo(token, owner, name, repo_description(day, topic))
    push_new_repo(token, owner, name, body)
    html_url = info.get("html_url") or f"https://github.com/{owner}/{name}"
    article = write_article(day, body + f"\n\n---\n本日独立仓库：{html_url}\n")
    rewrite_index(
        [{"date": day.isoformat(), "repo": f"{owner}/{name}", "url": html_url}]
    )
    git_publish_hub(
        [article, ARTICLES_DIR / "README.md", ARTICLES_DIR / "repos.json"],
        f"docs: 发布 {day.isoformat()} 仓库 {owner}/{name}",
    )
    print(f"已发布 {html_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
