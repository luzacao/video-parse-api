# 短视频去水印 API

把抖音、快手、豆包等平台的**分享链接**交给接口，返回无水印视频 / 图集直链、封面、作者信息。

在线文档（站内）：[https://video.zacao.top/docs](https://video.zacao.top/docs)  
购买 Key：[https://video.zacao.top/buy](https://video.zacao.top/buy)

> 仅用于你有权处理的素材（自己作品、已获授权内容）。请遵守各平台服务条款与当地法律。

---

## Base URL

```text
https://video.zacao.top
```

统一响应：

```json
{
  "code": 200,
  "message": "成功",
  "succ": true,
  "data": {}
}
```

首页网页体验可不带 Key，每个 IP 每小时限 30 次。正式对接请使用 API Key。

---

## 鉴权

| 方式 | 写法 |
| --- | --- |
| Header（推荐） | `X-API-Key: mp_xxxx` |
| Bearer | `Authorization: Bearer mp_xxxx` |
| Body / Query | `api_key=mp_xxxx` |

Key 无效或已禁用返回 `403`。服务端开启强制鉴权时，缺 Key 返回 `401`。

---

## 支持平台

重点覆盖：**抖音、快手、豆包**，并支持小红书、视频号、B 站、今日头条、TikTok、即梦、公众号、微博、西瓜、知乎、微视、梨视频、得物等 **30+** 平台。

常见链接形态：

| 平台 | 示例 |
| --- | --- |
| 抖音 | `https://v.douyin.com/xxxxx/`、`https://www.douyin.com/video/...` |
| 快手 | `https://v.kuaishou.com/xxxxx`、`https://www.kuaishou.com/short-video/...` |
| 豆包 | `https://www.doubao.com/...`、`https://www.dola.com/...` |

`text` 可以直接贴 App 里「复制链接」的整段分享文案，接口会自动抽出 URL。

---

## POST `/api/parse`

解析短视频 / 图文，返回无水印地址。

### 请求

```http
POST /api/parse
Content-Type: application/json
X-API-Key: mp_xxxx

{"text": "https://v.douyin.com/xxxxx/"}
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `text` | string | 是 | 分享文案或完整链接，也可用 `url` |

### 成功 `data`

| 字段 | 说明 |
| --- | --- |
| `platform` | 平台名，如 `抖音` / `快手` / `豆包` |
| `title` | 标题 |
| `video_id` | 平台侧作品 ID（如有） |
| `video_url` | 可播放地址（部分平台为站内流代理路径） |
| `source_video_url` | 原始视频地址 |
| `cover_url` | 封面 |
| `audio_url` | 音频（如有） |
| `image_list` | 图集；元素为 URL 字符串，或 `{url, live_photo_url}` |
| `author` | 作者信息对象 |

### curl

```bash
curl -X POST 'https://video.zacao.top/api/parse' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: mp_xxxx' \
  -d '{"text":"https://v.douyin.com/xxxxx/"}'
```

### Python

```python
import requests

resp = requests.post(
    "https://video.zacao.top/api/parse",
    headers={"X-API-Key": "mp_xxxx"},
    json={"text": "https://v.douyin.com/xxxxx/"},
    timeout=30,
)
data = resp.json()
print(data["data"]["platform"], data["data"]["video_url"])
```

### 成功示例

```json
{
  "code": 200,
  "message": "成功",
  "succ": true,
  "data": {
    "platform": "抖音",
    "title": "视频标题",
    "video_id": "7123...",
    "video_url": "https://...",
    "source_video_url": "https://...",
    "cover_url": "https://...",
    "audio_url": "https://...",
    "author": {
      "nickname": "作者昵称",
      "author_id": "作者ID",
      "avatar": "https://..."
    },
    "image_list": []
  }
}
```

---

## GET/POST `/api/parse/v2`

与 `/api/parse` 同一套解析逻辑，额外带兼容字段。

| 入参 | 说明 |
| --- | --- |
| POST body `text` | 分享文案 / 链接 |
| GET query `url` | 链接地址 |

额外字段：`url`、`sourceURL`、`streamUrl`、`imgUrls`、`sourceImgUrls`、`type`（`1`=视频，`0`=图文）。

```bash
curl 'https://video.zacao.top/api/parse/v2?url=https://v.douyin.com/xxxxx/' \
  -H 'X-API-Key: mp_xxxx'
```

---

## GET/POST `/api/detail`

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
| `title` | 标题 |
| `desc` | 正文 / 描述 |
| `type` | `video` / `image` / `note` |
| `publish_time` | Unix 秒 |
| `publish_time_str` | 北京时间 `YYYY-MM-DD HH:MM:SS` |
| `author` | nickname / author_id / avatar |
| `stats.like_count` | 点赞 |
| `stats.comment_count` | 评论 |
| `stats.collect_count` | 收藏 |
| `stats.share_count` | 分享 |
| `stats.play_count` | 播放 / 阅读（有则返回） |
| `cover_url` | 封面 |

---

## GET `/api/video/stream`

部分平台直链有防盗链，`/api/parse` 可能已经返回站内代理地址。也可自行走流代理：

```text
GET /api/video/stream?url=<encoded_video_url>&referer=<encoded_page_url>
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
curl 'https://video.zacao.top/api/health'
```

返回：`{"code":200,"message":"ok","succ":true}`

---

## 说明

- 解析结果里的直链可能有时效，建议拿到后尽快转存，不要长期缓存当 CDN 用。
- 豆包 / 部分平台的 `video_url` 可能是 `/api/video/stream?...` 代理路径，请拼上 Base URL 再播放。
- 本仓库只放对接文档，不含解析服务源码。
