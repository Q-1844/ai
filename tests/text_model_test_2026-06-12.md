# Agnes 2.0 Flash 官方文档对齐实测报告（2026-06-12 第三轮）

## 测试环境
- 模型：agnes-2.0-flash
- Endpoint：POST /v1/chat/completions
- 认证：Bearer Token

## 测试结果

| 序号 | 测试 | HTTP | 耗时 | 输出tokens | finish_reason | 状态 |
|---|---|---|---|---|---|---|
| 1 | 基础对话 | 200 | 8.6s | 725 | stop | ✅ |
| 2 | 流式输出 | 200 | 1.6s | 768 (144 chunks) | stop | ✅ |
| 3 | 工具调用 (get_weather) | 200 | 3.8s | 26 | tool_calls | ✅ |
| 4 | 图片URL输入 | 200 | 19.0s | 428 | stop | ✅ |
| 5 | Thinking (OpenAI格式) | 200 | 14.1s | 1078 | stop | ✅ |
| 6 | Thinking (Anthropic格式) | 200 | 1.2s | 13 | stop | ⚠️ 未触发thinking |
| 7 | 多轮对话 | 200 | 3.6s | 15 | stop | ✅ |
| 8 | JSON风格输出 | 200 | 1.3s | 30 | stop | ✅ |
| 9 | 长输出 max_tokens=4096 | 200 | 23.2s | 2136 | stop | ✅ |
| 10a | temperature=0 | 200 | 1.0s | 2 | stop | ✅ |
| 10b | temperature=1.5 | 200 | 1.1s | 2 | stop | ✅ |

## 关键发现

1. **图片理解确认可用**：`image_url` 输入正常，prompt_tokens 从 228 涨到 989
2. **工具调用正常**：返回 `tool_calls` + 结构化 `function.arguments`
3. **Thinking (OpenAI格式)** 正常：返回 `reasoning_content` 字段
4. **Thinking (Anthropic格式)** 未触发：可能需要特定路由或不支持
5. **上下文窗口是 256K**（官方文档明确，非第三方报道的 1M）
6. **价格**：标准 $0.03/$0.15 per 1M tokens，当前免费（$0）
