#!/usr/bin/env python3
"""每天生成一篇去水印 API 相关 Markdown，并推送到 GitHub。"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = ROOT / "articles"
README_PATH = ROOT / "README.md"

TOPICS = [
    "抖音分享链接解析与无水印下载对接注意事项",
    "快手短链 / 口令解析常见失败原因与重试建议",
    "豆包、即梦生成视频如何用分享链取无水印地址",
    "小红书图文笔记与实况图的 image_list 字段怎么用",
    "视频号、公众号链接解析边界与防盗链处理",
    "API Key、限流（每 IP 每小时 30 次）与错误码对照",
    "parse 与 parse/v2、detail、video/stream 该怎么选",
    "Python / curl 最小接入示例与直链过期提醒",
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


def topic_for(day: dt.date) -> str:
    return TOPICS[day.toordinal() % len(TOPICS)]


def call_deepseek(prompt: str) -> str:
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
                    "你是短视频去水印 API 的技术写作者。只输出完整 Markdown 正文，"
                    "不要包裹 ```markdown 代码围栏。不要编造未在资料中出现的接口路径。"
                    "语气清楚、可直接给开发者看。必须保留体验地址和访问密码。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
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


def build_prompt(day: dt.date, topic: str, api_readme: str) -> str:
    existing = sorted(p.name for p in ARTICLES_DIR.glob("*.md") if p.name != "README.md")
    recent = "、".join(existing[-8:]) if existing else "（暂无）"
    return f"""今天日期：{day.isoformat()}（北京时间）
今日主题：{topic}

请写一篇中文技术短文（约 800～1400 字），服务是「短视频去水印 API」。

固定信息（必须写进文中，不要改）：
- 体验地址：https://video.zacao.top
- 访问密码：zacao
- 文档：https://video.zacao.top/docs
- 购买 Key：https://video.zacao.top/buy
- 公开仓库：https://github.com/luzacao/video-parse-api
- Base URL：https://video.zacao.top
- 解析接口：POST /api/parse ，Header X-API-Key
- 首页体验可不带 Key，每个 IP 每小时 30 次

结构建议：
1. 标题（一级标题，带日期）
2. 今天解决什么问题
3. 对接步骤或示例（curl 或 Python 二选一即可）
4. 常见坑
5. 体验入口（含网址和密码）

已发布文章文件名（避免重复）：{recent}

以下是仓库当前 API README，接口以它为准：

{api_readme[:6000]}
"""


def write_article(day: dt.date, body: str) -> Path:
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTICLES_DIR / f"{day.isoformat()}.md"
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    return path


def rewrite_index() -> None:
    files = sorted(p for p in ARTICLES_DIR.glob("*.md") if p.name != "README.md")
    lines = [
        "# 每日文档",
        "",
        "由服务器每天 06:00（北京时间）调用 DeepSeek 生成，并推送到本仓库。",
        "",
    ]
    for p in reversed(files):
        title = p.stem
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        lines.append(f"- [{p.stem} · {title}]({p.name})")
    lines.append("")
    (ARTICLES_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def git_publish(paths: list[Path], message: str) -> None:
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
        print("无文件变更，跳过提交")
        return
    run(
        [
            "git",
            "-C",
            str(ROOT),
            "-c",
            "user.name=" + getenv("GIT_USER_NAME", "daily-publisher"),
            "-c",
            "user.email=" + getenv("GIT_USER_EMAIL", "daily-publisher@local"),
            "commit",
            "-m",
            message,
        ]
    )
    if not token:
        raise SystemExit("缺少 GITHUB_TOKEN，无法 push")
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    run(["git", "-C", str(ROOT), "push", url, "HEAD:main"])


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv(ROOT / ".env")
    day = today()
    topic = topic_for(day)
    api_readme = README_PATH.read_text(encoding="utf-8") if README_PATH.is_file() else ""
    print(f"生成 {day.isoformat()} 主题：{topic}", flush=True)
    body = call_deepseek(build_prompt(day, topic, api_readme))
    article = write_article(day, body)
    rewrite_index()
    git_publish(
        [article, ARTICLES_DIR / "README.md"],
        f"docs: 发布 {day.isoformat()} 去水印 API 日报",
    )
    print(f"已发布 {article.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
