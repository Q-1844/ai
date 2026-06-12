# Q-1844 / ai

> 测试与记录 Agnes AI（Sapiens AI）免费开放 API 的能力与限制。
>
> Base URL: `https://apihub.agnes-ai.com/v1` · 协议：OpenAI 兼容 · 免费无限期（不绑信用卡）

本仓库用于保留**实测数据**、**接口示例代码**、以及对各模型上界的观测结果。

---

## 一、可用模型总览（来自 `/v1/models`）

| 模型 | 类型 | 用途 |
|---|---|---|
| `agnes-2.0-flash` | 文本 | 对话、代码、Agent、工具调用（主力） |
| `agnes-1.5-flash` | 文本+多模态 | 轻量对话、图像理解 |
| `agnes-image-2.1-flash` | 图像（文生图） | 纯文→图生成 |
| `agnes-image-2.0-flash` | 图像（图生图） | 原图+指令编辑、换背景、局部编辑 |
| `agnes-video-v2.0` | 视频（文生视频 / 图生视频） | 短视频、分镜预演，含音画同步 |

---

## 二、关键实测结论（2026-06-12）

### 文本（agnes-2.0-flash）

- 简单 `ping` 请求的 `prompt_tokens` ≈ 210（含系统提示）。
- 连续 8 次请求全部成功（1.3s ~ 9.2s / 次），未触发硬限速。
- 响应头 **不** 包含标准 `X-RateLimit-*` 字段；只有 `x-litellm-key-spend: 0.0`，表明当前 key 走的是**免费通道**。
- 输出 `max_tokens` ≥ 4096 正常工作；更长上限未极限压测。
- 后台为 **LiteLLM → vLLM**（响应中可见 `system_fingerprint: vllm-0.21.0-...`）。

### 图像

| 项目 | 文生图（2.1-flash） | 图改图（2.0-flash） |
|---|---|---|
| 接口 | `POST /v1/images/generations` | `POST /v1/images/generations` + `extra_body.image` |
| 1024×1024 耗时 | ≈ 9.4 s | ≈ 52.9 s |
| 1792×1024 耗时 | ≈ 14.2 s | 未测 |
| 5248×2944（4K） | ❌ HTTP 500 · 97 s 超时（内测中） | 未测 |
| 输出格式 | PNG 公网 URL | PNG 公网 URL |
| `usage.total_tokens` | 0（未记账） | 4096（记账不稳） |

> 🚩 **坑**：文生图不要传 `extra_body`，会报 `UnsupportedParamsError`；图改图**必须**传 `extra_body.image: ["原图 URL"]`。

### 视频（agnes-video-v2.0）

- **异步工作流**：先 `POST /v1/videos` 拿 `task_id`，再 `GET /v1/videos/{task_id}` 轮询。
- `num_frames` 必须满足 `8n+1`（如 81/121/241/441），否则出错。
- 时长 = `num_frames / frame_rate`。默认 121 帧 @ 24 fps ≈ **5 秒**。
- 下载字段：多份第三方实测指出，完成时字段是 **`remixed_from_video_id`**（不是直觉的 `url` / `video_url`），代码里要做兼容。
- **本次实测**：任务创建后排队超过 **5 分钟**，`status` 始终 `queued`、`progress` 始终 `0`——免费用户队列可能较长，或该模型当前处于不可用/降级状态。

---

## 三、免费额度与限制（多来源交叉）

| 来源 | 文本 | 图像 | 视频 | 限速 |
|---|---|---|---|---|
| 官方最新说法 | 无限期免费 | 无限期免费 | 无限期免费 | 仅 RPM（每分钟请求数） |
| 第三方报道 A | 无限 | 每月 500 张 | 首月 100 秒 | — |
| 第三方报道 B | 3 款模型合计 **620 次 / 天 / 账号** | 同左 | 同左 | 每日总量 |
| 本次实测 | 连测 8 次通过 | 2 张成功 | 1 个任务排队 > 5 min | 未触发硬上限 |

> ⚠️ 不同渠道说法不一致。稳妥用法：自己加重试 + 指数退避；不要把它当 100% SLA 的基础设施。

---

## 四、快速上手（Python）

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-K3M3...（你的 Agnes API Key）",
    base_url="https://apihub.agnes-ai.com/v1",
)

# 1) 文本
r = client.chat.completions.create(
    model="agnes-2.0-flash",
    messages=[{"role": "user", "content": "用 Python 写一个 LRU 缓存"}],
    max_tokens=4096,
    temperature=0.2,
)
print(r.choices[0].message.content)

# 2) 文生图
img = client.images.generate(
    model="agnes-image-2.1-flash",
    prompt="一只橘色的猫坐在窗台上，阳光洒在它身上，背景是城市景观，摄影风格，暖色调",
    size="1024x1024",
)
print(img.data[0].url)

# 3) 图改图
edit = client.images.generate(
    model="agnes-image-2.0-flash",
    prompt="保留小猫和足球不变，把场景改成傍晚的专业足球场，电影感",
    size="1024x1024",
    extra_body={"image": ["https://.../原图.png"]},
)
print(edit.data[0].url)

# 4) 视频（异步，需手动轮询，OpenAI SDK 未封装）
#    见 AGNES_MODELS.md 的 curl + requests 示例
```

更多接口细节、参数边界、踩坑记录见 [AGNES_MODELS.md](./AGNES_MODELS.md)。


---

## 附录：视频生成并发实测记录（2026-06-12）

### 目标
验证 `agnes-video-v2.0` 在 10 并发下的创建成功率、队列等待时长、实际出片时间。

### 快速结论
- 10 并发 POST → **9 条成功创建**，1 条 60 秒超时失败。
- 10 分钟观察窗内 **0/9 条完成**，全部维持 `status=queued, progress=0`。
- 响应无 `X-RateLimit-*` 头，无法读取余量。
- 完整报告见 [tests/video_concurrency_10_2026-06-12.md](./tests/video_concurrency_10_2026-06-12.md)。

### 建议
- **不要** 一次性盲发 100 个视频任务，提交阶段已有超时。
- 把观察窗拉长到 **30–60 分钟**再测一次，以判断队列是"会慢慢吐"还是"永远卡住"。
- 关键业务上多供应商兜底（Agnes 做低价试产层）。
