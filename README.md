# 短视频去水印 API

把抖音、快手、豆包（豆包）等平台的**分享链接**交给接口，返回无水印视频 / 图集 / 封面地址。

在线文档：[https://video.zacao.top/docs](https://video.zacao.top/docs)  
购买 Key：[https://video.zacao.top/buy](https://video.zacao.top/buy)

---

## 能解析什么

粘贴 App 里「复制链接」得到的口令或 URL 即可，不必先拆出真实地址。

| 平台 | 说明 |
| --- | --- |
| **抖音** | 短链 `v.douyin.com`、图集、实况 |
| **快手** | `v.kuaishou.com` 等分享链 |
| **豆包 / 豆包** | `doubao.com`、`dola.com` 分享的生成视频 |
| 即梦 | `jimeng.jianying.com` |
| 小红书 | 图文 / 视频笔记 |
| 视频号 / 公众号 | 微信侧分享链 |
| B 站、头条、西瓜、微博、微视、得物、TikTok 等 | 共 30+ 平台 |

链接识别按域名自动分流，调用方不用传 `platform`。

---

## 接入说明

**Base URL**

```text
https://video.zacao.top
```

**统一响应**

```json
{
  "code": 200,
  "message": "成功",
  "succ": true,
  "data": {}
}
```

首页网页体验可以不带 Key，每个 IP 每小时限 30 次。正式对接请使用 API Key。

---

## 鉴权

在 [购买页](https://video.zacao.top/buy) 自助下单，或由服务方发放。请求时任选一种：

| 方式 | 写法 |
| --- | --- |
| Header（推荐） | `X-API-Key: mp_xxxx` |
| Bearer | `Authorization: Bearer mp_xxxx` |
| Body / Query | `api_key=mp_xxxx` |

无效或已禁用的 Key 返回 `403`。服务端开启强制鉴权后，无 Key 返回 `401`。

---

## 解析接口

### `POST /api/parse`

解析短视频 / 图文，返回无水印地址。

**请求**

```http
POST /api/parse
Content-Type: application/json
X-API-Key: mp_xxxx

{"text": "https://v.douyin.com/xxxxx/"}
```

`text` 也可以换成 `url`。可以直接丢整段分享口令，接口会从文案里抽出链接。

**`data` 字段**

| 字段 | 说明 |
| --- | --- |
| `platform` | 平台名，如 `抖音`、`快手`、`豆包` |
| `title` | 标题 |
| `video_url` | 可播放地址（部分平台为站内代理路径） |
| `source_video_url` | 原始视频地址 |
| `cover_url` | 封面 |
| `audio_url` | 音频（如有） |
| `image_list` | 图集；元素为字符串，或 `{ "url", "live_photo_url" }` |
| `author` | 作者信息 |
| `video_id` | 平台侧作品 ID（如有） |

**curl**

```bash
curl -X POST 'https://video.zacao.top/api/parse' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: mp_xxxx' \
  -d '{"text":"9.01 复制打开抖音，看看https://v.douyin.com/xxxxx/"}'
```

**Python**

```python
import requests

r = requests.post(
    "https://video.zacao.top/api/parse",
    headers={"X-API-Key": "mp_xxxx"},
    json={"text": "https://v.kuaishou.com/xxxxx"},
    timeout=30,
)
print(r.json())
```

**成功示例（抖音）**

```json
{
  "code": 200,
  "message": "成功",
  "succ": true,
  "data": {
    "video_id": "7123...",
    "platform": "抖音",
    "title": "视频标题",
    "video_url": "https://...",
    "source_video_url": "https://...",
    "audio_url": "https://...",
    "cover_url": "https://...",
    "author": {
      "nickname": "作者",
      "author_id": "...",
      "avatar": "https://..."
    },
    "image_list": []
  }
}
```

---

### `GET|POST /api/parse/v2`

解析逻辑与 `/api/parse` 相同，额外带一批兼容字段，方便旧客户端对接。

| 入参 | 说明 |
| --- | --- |
| POST body `text` / `url` | 分享文案或链接 |
| GET query `url` / `text` | 同上 |

额外字段：

| 字段 | 说明 |
| --- | --- |
| `url` | 同 `video_url` |
| `sourceURL` | 同 `source_video_url` |
| `streamUrl` | 走了站内代理时的播放地址，否则为空 |
| `imgUrls` / `sourceImgUrls` | 图集 URL 列表 |
| `type` | `1` = 视频，`0` = 图文 |

```bash
curl 'https://video.zacao.top/api/parse/v2?url=https://www.doubao.com/thread/xxxxx' \
  -H 'X-API-Key: mp_xxxx'
```

---

### `GET|POST /api/detail`

作品详情：标题、发布时间、作者、点赞 / 评论 / 收藏 / 分享 / 播放量。  
目前支持 **抖音、小红书、视频号**。不返回视频或图片直链。

```bash
curl -X POST 'https://video.zacao.top/api/detail' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: mp_xxxx' \
  -d '{"text":"https://v.douyin.com/xxxxx/"}'
```

| 字段 | 说明 |
| --- | --- |
| `platform` | 抖音 / 小红书 / 视频号 |
| `work_id` | 作品 ID |
| `title` / `desc` | 标题、正文 |
| `type` | `video` / `image` / `note` |
| `publish_time` | Unix 秒 |
| `publish_time_str` | 北京时间 `YYYY-MM-DD HH:MM:SS` |
| `author` | nickname / author_id / avatar |
| `stats.like_count` | 点赞 |
| `stats.comment_count` | 评论 |
| `stats.collect_count` | 收藏 |
| `stats.share_count` | 分享 / 转发 |
| `stats.play_count` | 播放 / 阅读（有则返回） |
| `cover_url` | 封面 |

---

### `GET /api/video/stream`

部分平台直链有防盗链，`/api/parse` 可能已经把 `video_url` 换成站内代理路径。也可以自己调：

```text
GET /api/video/stream?url=<urlencoded>&referer=<urlencoded>
```

| 参数 | 说明 |
| --- | --- |
| `url` | 源视频地址（需 URL 编码） |
| `referer` | 可选，源站 Referer |

---

## 错误码

| code / HTTP | 含义 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误 / 链接不支持 |
| 401 | 缺少 API Key（强制鉴权时） |
| 403 | Key 无效、禁用，或内容不可访问 |
| 404 | 内容可能已删除 |
| 429 | 匿名 IP 小时额度用尽（默认 30 次） |
| 500 / 502 | 服务异常或抓取失败 |

探活：

```bash
curl https://video.zacao.top/api/health
```

---

## 使用注意

1. 直链有时效，解析成功后请尽快转存，不要把 `source_video_url` 当永久地址缓存。
2. 豆包 / 即梦等生成内容，请使用 App 或网页里的**分享链接**，不要传对话页的内部 URL。
3. 快手、小红书短链有时需要完整口令；解析失败时让用户重新复制一次分享文案。
4. 仅用于已获授权的素材提取、备份与学习。请遵守各平台用户协议与著作权法，不要把本接口用于侵权搬运。
