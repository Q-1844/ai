# Agnes AI 各模型详细参数 / 实测边界

> 测试时间：2026-06-12（第二轮，按官方文档对齐）
> Base URL：`https://apihub.agnes-ai.com`
> 认证：`Authorization: Bearer sk-...`

---

## 1. `agnes-2.0-flash`（文本主力）

### 定位
面向智能体工作流、工具调用、编程、推理的生产级语言模型。Claw-Eval General Leaderboard 第 9，Pass³ 60.9%。

### 参数
| 项 | 推荐值 |
|---|---|
| `temperature` | 确定性 0.1-0.3，创意 0.7-0.9 |
| `top_p` | 1.0（默认） |
| `max_tokens` | ≤ 4096 实测稳定；文档上限 65,536 |
| `stream` | 支持 |
| `tools` / `tool_choice` | 支持 |
| `thinking`（扩展参数） | 文档提到，可显著提升复杂任务质量 |

### 性能
- 文档上下文：**1,048,576 tokens（约 75 万字）**
- 单实例 TPS：约 200+，高并发峰值 800
- 实测响应时间：1.3 ~ 9.2 秒（简 prompt）

### 响应头特征
```
x-litellm-key-spend: 0.0                  # 免费通道，不计费
x-litellm-model-group: agnes-2.0-flash
system_fingerprint: vllm-0.21.0-tp2-...    # 推理层是 vLLM
```

---

## 2. `agnes-1.5-flash`（轻量文本 + 图像理解）

### 定位
轻量文本模型，**多模态**（支持图像输入），无 Thinking 模式，面向即时问答。

### 与 2.0-flash 的区别
- 缺少 Thinking 模式 → 复杂推理不如 2.0
- 原生支持图像理解 → 看图/文档截图问答用它
- 响应时间相仿

---

## 3. `agnes-image-2.1-flash`（文生图 + 图生图）

### ⚠️ 关键踩坑（2026-06-12 实测）

1. **`response_format` 不能放请求体顶层**，必须放 `extra_body` 里，否则 400。
2. **图生图时，输入图片放顶层 `image` 数组**（不是 `extra_body.image`）——两种方式都能跑，但**顶层 `image` 快 7 倍**（7.3s vs 49s）。
3. **不需要传 `tags: ["img2img"]`**。
4. **文生图 Base64 输出**用顶层 `return_base64: true`；**图生图 Base64 输出**用 `extra_body.response_format: "b64_json"`。
5. **非法尺寸（如 500x500）会超时**，不会返回明确错误。

### 接口
```
POST https://apihub.agnes-ai.com/v1/images/generations
```

### 请求参数
| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `model` | string | ✅ | 固定 `agnes-image-2.1-flash` |
| `prompt` | string | ✅ | 图片生成/编辑提示词 |
| `size` | string | ✅ | 输出尺寸，如 `1024x768` |
| `image` | string[] | 图生图必填 | 输入图片数组（**顶层字段**），支持公网 URL 或 Data URI Base64 |
| `return_base64` | boolean | ❌ | 文生图需要 Base64 输出时设为 `true` |
| `extra_body.response_format` | string | ❌ | `"url"` 或 `"b64_json"` |
| `extra_body.image` | string[] | ❌ | 旧方式，仍可用但**慢 7 倍**，不推荐 |

### 实测耗时（2026-06-12）

| 测试 | 尺寸 | 方式 | 耗时 | HTTP |
|---|---|---|---|---|
| 文生图 URL | 1024x768 | `extra_body.response_format="url"` | **7.4s** | 200 |
| 文生图 Base64 | 1024x768 | `return_base64=true` | **7.7s** | 200 |
| 文生图 URL | 1024x1024 | 同上 | **19.7s** | 200 |
| 文生图 URL | 1792x1024 | 同上 | **15.4s** | 200 |
| 文生图 URL | 1024x1792 | 同上 | **14.7s** | 200 |
| 文生图 URL | 1536x1024 | 同上 | **24.6s** | 200 |
| 图生图（顶层 `image`）URL | 1024x768 | `image=[url]` | **7.3s** | 200 |
| 图生图（`extra_body.image`）URL | 1024x768 | `extra_body.image=[url]` | **49.0s** | 200 |
| 图生图 Base64 | 1024x768 | `image=[url]` + `b64_json` | **42.6s** | 200 |
| 非法尺寸 500x500 | 500x500 | — | **60s 超时** | 0 |

### 推荐调用方式

**文生图 URL 输出：**
```bash
curl https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash",
       "prompt":"A luminous floating city above a misty canyon at sunrise",
       "size":"1024x768",
       "extra_body":{"response_format":"url"}}'
```

**文生图 Base64 输出：**
```bash
curl https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash",
       "prompt":"A clean product photo of a glass cube",
       "size":"1024x768",
       "return_base64":true}'
```

**图生图 URL 输出（推荐：顶层 `image`）：**
```bash
curl https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash",
       "prompt":"Transform into cyberpunk night while preserving composition",
       "size":"1024x768",
       "image":["https://example.com/input.png"],
       "extra_body":{"response_format":"url"}}'
```

**图生图 Base64 输出：**
```bash
curl https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-image-2.1-flash",
       "prompt":"Convert to watercolor style while preserving composition",
       "size":"1024x768",
       "image":["https://example.com/input.png"],
       "extra_body":{"response_format":"b64_json"}}'
```

### 返回格式

**URL 输出：**
```json
{"created":1780000000,"data":[{"url":"https://storage.googleapis.com/agnes-aigc/xxx.png","b64_json":null,"revised_prompt":null}]}
```

**Base64 输出：**
```json
{"created":1780000000,"data":[{"url":null,"b64_json":"iVBORw0KGgoAAAANSUhEUgAA...","revised_prompt":null}]}
```

### Prompt 最佳实践

**文生图**：`[主体] + [场景/环境] + [风格] + [光照] + [构图] + [质量要求]`

**图生图**：`[修改要求] + [新风格/新场景] + [需要添加或移除的元素] + while preserving the original composition`

---

## 4. `agnes-image-2.0-flash`（旧版图生图）

> 此模型已被 `agnes-image-2.1-flash` 替代。2.1 同时支持文生图和图生图，推荐统一使用 2.1。
> 旧版 2.0 仅支持图生图，且需要 `extra_body.image`，速度更慢（~53s）。

---

## 5. `agnes-video-v2.0`（视频生成 + 音频同步）

### ⚠️ 查询接口踩坑（重要）

| 接口 | 行为 |
|---|---|
| `GET /agnesapi?video_id=<VIDEO_ID>&model_name=agnes-video-v2.0`（**官方推荐**） | 状态**实时**更新，5s 轮询即可 |
| `GET /v1/videos/{task_id}`（旧/兼容） | 状态更新**严重延迟**，可能永远显示 `queued` |

**务必用 `video_id` 查新接口！** 用 `task_id` 查旧接口会误导你判任务失败。

### 工作流（异步）

```
# 1. 创建任务 -> 拿到 task_id 和 video_id
POST /v1/videos
  -> { "id": "task_xxx", "video_id": "video_xxx", "status": "queued" }

# 2. 轮询（5s 间隔，用 video_id）
GET /agnesapi?video_id=video_xxx&model_name=agnes-video-v2.0
  -> { "status": "completed", "remixed_from_video_id": "https://...mp4" }
```

### 创建任务参数
| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `model` | string | ✅ | 固定 `agnes-video-v2.0` |
| `prompt` | string | ✅ | 视频内容描述 |
| `image` | string / array | ❌ | 图生视频时传入图片 URL |
| `height` | integer | ❌ | 默认 768，需被 64 整除 |
| `width` | integer | ❌ | 默认 1152，需被 64 整除 |
| `num_frames` | integer | ❌ | **必须 8n+1**，≤441 |
| `frame_rate` | number | ❌ | 1-60，推荐 24 |
| `negative_prompt` | string | ❌ | 负向提示词 |
| `seed` | integer | ❌ | 随机种子 |
| `extra_body.image` | array | ❌ | 多图视频/关键帧模式 |
| `extra_body.mode` | string | ❌ | 如 `"keyframes"` |

### 时长计算
```
seconds = num_frames / frame_rate
```

| 目标时长 | num_frames | frame_rate |
|---|---|---|
| ~3s | 81 | 24 |
| ~5s | 121 | 24 |
| ~10s | 241 | 24 |
| ~18s | 441 | 24 |

### 实测耗时（2026-06-12，新接口轮询）

| 测试 | 创建耗时 | 出片耗时 | HTTP | 状态 |
|---|---|---|---|---|
| 文生视频 5s (121帧) | 1.9s | ~90s | 200 | ✅ completed |
| 文生视频 10s (241帧) | 1.0s | ~170s | 200 | ✅ completed |
| 图生视频 (image=URL) | 20.7s | ~105s | 200 | ✅ completed |
| 文生视频 3s (81帧) | 3.3s | ~105s | 200 | ✅ completed |
| 文生视频 + negative_prompt | 1.2s | ~105s | 200 | ✅ completed |
| 文生视频 + seed=42 | 4.3s | ~90s | 200 | ✅ completed |

**6/6 全部 completed，5s 视频约 1.5 分钟出片，10s 视频约 3 分钟。**

### 推荐调用方式

**文生视频：**
```bash
curl -X POST https://apihub.agnes-ai.com/v1/videos \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-video-v2.0",
       "prompt":"A cinematic shot of a cat walking on the beach at sunset",
       "height":768,"width":1152,"num_frames":121,"frame_rate":24}'
```

**图生视频：**
```bash
curl -X POST https://apihub.agnes-ai.com/v1/videos \
  -H "Authorization: Bearer sk-..." -H "Content-Type: application/json" \
  -d '{"model":"agnes-video-v2.0",
       "prompt":"The cat slowly turns its head, natural motion",
       "image":"https://example.com/cat.png",
       "num_frames":121,"frame_rate":24}'
```

**轮询（推荐方式）：**
```bash
curl "https://apihub.agnes-ai.com/agnesapi?video_id=VIDEO_ID&model_name=agnes-video-v2.0" \
  -H "Authorization: Bearer sk-..."
# 完成时: status="completed", remixed_from_video_id="https://...mp4"
```

### 完成响应
```json
{
  "id": "task_xxx",
  "video_id": "video_xxx",
  "status": "completed",
  "progress": 100,
  "seconds": "5.0",
  "size": "1152x768",
  "remixed_from_video_id": "https://storage.googleapis.com/agnes-aigc/.../video_xxx.mp4",
  "error": null
}
```

### 任务状态
| 状态 | 说明 |
|---|---|
| `queued` | 等待中 |
| `in_progress` | 生成中 |
| `completed` | 已完成，`remixed_from_video_id` 可用 |
| `failed` | 失败，查看 `error` |

---

## 6. 常见错误码

| HTTP | 常见原因 |
|---|---|
| 400 | `response_format` 放顶层、参数格式错误 |
| 401 | Token 无效/过期 |
| 404 | 视频查询用错 video_id、图像模型接到 chat 端点 |
| 429 | RPM 限流，稍后重试 |
| 500 | 上游推理错误（如 4K 图片），重试 |
| 超时 | 非法尺寸、服务端负载高 |

---

## 7. 限额与策略

- **最新官方口径**：核心模型长期免费，限速仅按 RPM。
- **第三方报道**：文本无限，图像每月 500 张，视频首月 100 秒。
- **本次实测**：未触及硬上限；响应头无 `X-RateLimit-*`。

### 工程建议
1. 对 `429 / 500` 做指数退避重试（1s → 2s → 4s → 8s，最多 5 轮）。
2. 视频轮询用 `GET /agnesapi?video_id=...`，间隔 5s，超时阈值 ≥ 5 分钟。
3. 图生图用顶层 `image` 字段（比 `extra_body.image` 快 7 倍）。
4. `response_format` 永远放 `extra_body` 里。
5. 重要内容在 Agnes 之上再挂一个主流闭源模型作为 fallback。

---

## 8. 与主流模型对标

| 维度 | Agnes-2.0-Flash | GPT-4o | Claude 3.5 Sonnet | Gemini 2.0 Flash |
|---|---|---|---|---|
| 价格 | **免费** | $2.5/1M tok | $3/1M tok | $0.15/1M tok |
| 上下文 | **1M** | 128K | 200K | 1M |
| 推理质量 | 中上 | 顶尖 | 顶尖 | 中上 |
| 视频生成 | **原生含音频** | 需另买 Sora | 无 | 含 Veo |
| 图像生成 | **原生含** | DALL-E 另计 | 无 | Imagen 另计 |
