# Agnes AI 各模型详细参数 / 实测边界

> 测试时间：2026-06-12
> Base URL：`https://apihub.agnes-ai.com/v1`

---

## 1. `agnes-2.0-flash`（文本主力）

### 定位
面向智能体工作流、工具调用、编程、推理的生产级语言模型。文档宣称 Claw-Eval General Leaderboard 第 9、Pass³ 60.9%。

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
x-litellm-response-duration-ms: ...
system_fingerprint: vllm-0.21.0-tp2-...    # 推理层是 vLLM
```

---

## 2. `agnes-1.5-flash`（轻量文本 + 图像理解）

### 定位
轻量文本模型，**多模态**（支持图像输入），无 Thinking 模式，面向即时问答。

### 参数
| 项 | 值 |
|---|---|
| 上下文 | 约 128K（文档未明确定量） |
| 图像输入 | 支持（URL 或 base64） |
| Tool Calling | 弱或不支持 |

### 与 2.0-flash 的区别
- 缺少 Thinking 模式 → 复杂推理不如 2.0
- 原生支持图像理解 → 看图/文档截图问答用它
- 响应时间相仿

---

## 3. `agnes-image-2.1-flash`（文生图）

### 接口
```
POST https://apihub.agnes-ai.com/v1/images/generations
Content-Type: application/json
Authorization: Bearer sk-...

{
  "model": "agnes-image-2.1-flash",
  "prompt": "一只可爱的柴犬在樱花树下睡觉，温暖的阳光，柔和的粉色花瓣飘落",
  "size": "1024x1024",
  "n": 1
}
```

### 支持的 `size`
- `1024x1024`（方，实测 ≈ 9.4s）
- `1792x1024`（横，实测 ≈ 14.2s）
- `1024x1792`（竖）
- `1536x1024`、`1024x1536`
- `5248x2944`（4K，**内测**，本次测试 HTTP 500）

### 不要做的事
文生图时**不要传 `extra_body`**，会触发 `UnsupportedParamsError`。`extra_body` 仅用于图生图（2.0-flash）。

---

## 4. `agnes-image-2.0-flash`（图生图 / 图像编辑）

### 接口
```
POST https://apihub.agnes-ai.com/v1/images/generations

{
  "model": "agnes-image-2.0-flash",
  "prompt": "保留小猫踢足球动作不变，把场景改成傍晚的专业足球场，电影感",
  "size": "1024x1024",
  "extra_body": {
    "image": ["https://.../原图.png"]
  }
}
```

### 能力（文档宣称）
- 局部编辑 / 抠图 / 换背景
- **身份一致性**：修改造型时能稳定保留人物面部特征
- 高信息密度插图（表格、图示类素材）

### 实测耗时
1024×1024 编辑 ≈ **52.9 秒**（明显慢于文生图）。

---

## ⚠️ 视频查询接口踩坑（重要 · 2026-06-12 实测发现）

Agnes 的视频状态查询有两个接口，行为**不一致**：

| 接口 | 行为 |
|---|---|
| `GET /v1/videos/{task_id}`（旧/兼容） | 状态更新**严重延迟**，常卡在 `queued` 长达 25+ 分钟；我们 9 个任务测试时，前 10 分钟此接口全部返回 `queued`，但**任务其实早已 completed** |
| `GET /agnesapi?video_id=<video_id>&model_name=agnes-video-v2.0`（**官方推荐**） | 状态**实时**更新，首次响应就是 `completed` + `remixed_from_video_id` |

### 推荐做法

```python
# Step 1: 建任务 -> 同时拿到 task_id 和 video_id
resp = post("/v1/videos", body)
task_id  = resp["id"]
video_id = resp["video_id"]   # ← 关键字段，记下来

# Step 2: 轮询（间隔 5s）— 用 video_id
while True:
    r = get(f"/agnesapi?video_id={video_id}&model_name=agnes-video-v2.0")
    if r["status"] == "completed":
        url = r["remixed_from_video_id"]      # ← 这就是 mp4 直链
        break
    elif r["status"] == "failed":
        raise Exception(r.get("error"))
    sleep(5)
```

### 本次 9 任务最终结果（距离提交 ≈ 25~30 分钟后）

- **6 / 9 已 completed**，下载链接可用（已下载到本地，562 KB – 1.6 MB）
- **3 / 9 仍 queued**（5 分钟 ~ 25 分钟观察窗内没出片，可能进入更长队列）

### 结论

- **不是免费的不会出片**，而是**轮询接口一定要用 `video_id` 查 `agnesapi`**
- 用 `task_id` 查 `/v1/videos/{task_id}` 是"历史兼容"，数据可能严重滞后
- 实际处理时间 5 秒视频大约 1–2 分钟（不是 25 分钟；25 分钟是因为我们一直在拿错的接口查）

---

## 5. `agnes-video-v2.0`（视频生成 + 音频同步）

### 工作流（重要：**异步**）
```
# 1. 创建任务
POST /v1/videos
  -> 200 OK { "id": "task_xxx", "status": "queued", ... }

# 2. 轮询（每 30s 一次）
GET /v1/videos/task_xxx
  -> { "status": "queued|processing|completed|error",
        "progress": 0..100,
        "remixed_from_video_id": "https://.../最终视频.mp4" }
```

### 请求参数
| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string | 固定 `agnes-video-v2.0` |
| `prompt` | string | 视频内容描述（建议英文，或中文；实测都可） |
| `width` | int | 默认 1152；需被 64 整除 |
| `height` | int | 默认 768；需被 64 整除 |
| `num_frames` | int | **必须 8n+1**：81 / 121 / 241 / 441（越长越慢） |
| `frame_rate` | int | 1-60，推荐 24 |
| `image`（可选） | string[] | 图生视频时传入关键帧 URL |

### 时长计算
```
seconds = num_frames / frame_rate
```
常用搭配：121 帧 @ 24fps ≈ **5.0 秒**；441 帧 @ 24fps ≈ **18 秒**。

### 本次实测（task_AtXdLRa9Nx78wHVPNuZSiuTNulyBK0Db）
- 创建时间：1781233077（2026-06-12 约 02:37 UTC）
- `num_frames: 121`, `frame_rate: 24`, 尺寸 1152×768
- 5 分钟后：`status="queued"`, `progress=0`, `remixed_from_video_id=null`
- **结论**：免费用户的视频队列等待时间**远超文档宣称的 1-3 分钟**。实际项目要预留超时；或改用图生视频路径（参考图改图的稳定链路）。

### 字段名陷阱
- 文档写的完成字段可能叫 `video_url`，但第三方实测实际返回 `remixed_from_video_id`。
- **推荐写法**：`result.get("video_url") or result.get("remixed_from_video_id")`。

---

## 6. 完整 curl 模板（不依赖任何 SDK）

### 文本
```bash
curl https://apihub.agnes-ai.com/v1/chat/completions   -H "Authorization: Bearer sk-..."   -H "Content-Type: application/json"   -d '{"model":"agnes-2.0-flash",
       "messages":[{"role":"user","content":"你好"}],
       "max_tokens":512}'
```

### 文生图
```bash
curl https://apihub.agnes-ai.com/v1/images/generations   -H "Authorization: Bearer sk-..."   -H "Content-Type: application/json"   -d '{"model":"agnes-image-2.1-flash",
       "prompt":"一只柴犬在樱花树下睡觉",
       "size":"1024x1024","n":1}'
```

### 视频（两步）
```bash
# Step 1
curl -X POST https://apihub.agnes-ai.com/v1/videos   -H "Authorization: Bearer sk-..." -H "Content-Type: application/json"   -d '{"model":"agnes-video-v2.0",
       "prompt":"A cute orange cat sitting on a windowsill",
       "width":1152,"height":768,"num_frames":121,"frame_rate":24}'
# 拿到 task_id 后：
TASK_ID=task_AtXdLRa9Nx78wHVPNuZSiuTNulyBK0Db
for i in $(seq 1 20); do
  curl -sS "https://apihub.agnes-ai.com/v1/videos/$TASK_ID"     -H "Authorization: Bearer sk-..."
  echo; sleep 30
done
```

---

## 7. 常见错误码速查

| HTTP | 现象 | 常见原因 |
|---|---|---|
| 401 | `Bad credentials`（GitHub 侧）或 `Invalid token` | Token 写错 / 过期 / 权限不足 |
| 404 | `NotFoundError` / `Not Found` | 图像/视频模型被接到了 chat 端点，或尺寸参数不支持 |
| 429 | `Try again in X seconds` | 触发 RPM 限流 / 上游队列满 |
| 500 | `InternalServerError: OpenAIException` | 上游推理端出问题（比如 4K 图片），重试 |
| 视频长时间 `queued` | `status=queued, progress=0`（>5 分钟） | 免费用户队列积压，或模型当前降级 |

---

## 8. 限额与策略（多来源交叉）

- **最新官方口径**：核心模型「长期免费，无限期」，限速仅按 **RPM**。
- **第三方报道 1**：文本无限，图像每月 500 张，视频首月 100 秒。
- **第三方报道 2**：三模型合计 620 次 / 天 / 账号。
- **本次实测**：未触及硬上限；响应头无任何 `X-RateLimit-*`。

### 稳妥的工程建议
1. 对 `429 / 500` 做**指数退避重试**（1s → 2s → 4s → 8s，最多 5 轮）。
2. 不要把图像 / 视频接口当实时流水线使用（几十秒量级耗时）。
3. 重要内容在 Agnes 之上再挂一个主流闭源模型作为 fallback。
4. 视频任务超时阈值设为 **≥ 5 分钟**；若 10 分钟后仍 `queued`，可视为失败。

---

## 9. 与主流模型的大致对标（非严谨，仅给你选型直觉）

| 维度 | Agnes-2.0-Flash | GPT-4o | Claude 3.5 Sonnet | Gemini 2.0 Flash |
|---|---|---|---|---|
| 价格（约） | **免费** | $2.5 / 1M tok | $3 / 1M tok | $0.15 / 1M tok |
| 上下文 | **1M** | 128K | 200K | 1M |
| 推理质量 | 中上 | 顶尖 | 顶尖 | 中上 |
| 代码能力 | 可做主力 | 强 | 强 | 强 |
| 视频生成 | **原生含音频** | 需另买 Sora | 无 | 含 Veo |

---

## 10. 本仓库的 GitHub Token 与安全提醒

`sk-...` 类型的 Key 不要写进仓库；用环境变量或密钥管理工具。  
示例代码里的 `sk-K3M3...` 只是占位，请替换为你自己的凭据。
