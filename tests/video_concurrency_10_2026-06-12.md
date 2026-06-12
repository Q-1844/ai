# Agnes Video · 10 并发实测报告

> 测试时间：2026-06-12（UTC）
> 任务参数：`agnes-video-v2.0` · 1152×768 · `num_frames=121` · `frame_rate=24`（≈ 5 秒/条）
> 观察窗口：10 分钟（600 秒）

## 一、提交阶段（并发 POST）

| 序号 | HTTP 状态 | task_id | 耗时 |
|---|---|---|---|
| 0 | 200 | `task_e1cOzj7AhLkmZMR3HMKtslWvVwcn0tdL` | 1.3 s |
| 1 | 200 | `task_H9I7bv349a00mEkeFhaQFxY7euxB9Smz` | 1.2 s |
| 2 | 200 | `task_prlLCjLJnpRBL8tl5TbORQ2xuNUjGXAv` | 2.6 s |
| 3 | 200 | `task_m90xHSP2MKxD9w68q4QrDnTBzBeBdHoA` | 1.2 s |
| 4 | **0（socket 超时 60s）** | **创建失败** | 60.7 s |
| 5 | 200 | `task_WJaL3Em0SqUtsQt2oAyHHDzAYzac3Vwu` | 1.4 s |
| 6 | 200 | `task_ovPFDc1Q5XC79R8tlKlHTMM2HVdINMCo` | 9.2 s |
| 7 | 200 | `task_vUmGvZbUiU8VZTbQAstINtgbtQbRb958` | 1.2 s |
| 8 | 200 | `task_9HXfZJWNAKermgiEgw3VlOTYsb1rqVBt` | 32.8 s |
| 9 | 200 | `task_QU503a9rjRcpGL2o31jB0axySWiRhhos` | 1.4 s |

- **9 / 10 成功创建**，1 个 POST 超时（60 秒后仍无响应）。
- 创建耗时分布：1.2 ~ 32.8 s，其中 1 个 9.2 s、1 个 32.8 s ——POST 已经出现抖动。

## 二、轮询阶段（10 分钟观察窗）

每个任务返回字段一致：
```
status: queued
progress: 0
remixed_from_video_id: null
error: null
seconds: 5.0
size: 1152x768
```

| 轮次 | 相对开始时间 | 状态分布 |
|---|---|---|
| 1 | 63 s | queued=9 |
| 5 | 152 s | queued=9 |
| 10 | 264 s | queued=9 |
| 15 | 377 s | queued=9 |
| 20 | 487 s | queued=9 |
| 25 | 601 s | queued=9 |

- 10 分钟内 **0/9 进入 processing**，0/9 完成。
- 没有任何任务报错（error=null），也没有任何任务返回下载链接。
- 中间有 1 轮某个任务短暂被解析为 "unknown"，疑似网络抖动——后面又回到 queued，说明任务仍然存在。

## 三、结论

| 问题 | 本次实测答案 |
|---|---|
| 免费 key 能扛 10 并发 POST 吗？ | **勉强能**：9/10 成功，1 个 60s 超时 |
| 10 个任务能进入处理吗？ | **不能**：10 分钟观察窗内全为 `queued, progress=0` |
| 平均处理一个 5s 视频要多久？ | **未知**（没有 1 条完成，无法估算） |
| 是否能"并发 100 条慢慢等"？ | **不建议赌**——提交阶段已有超时/抖动；即便全提交成功，也会在队列里无限等待 |
| 响应头有没有额度提示？ | 没有 `X-RateLimit-*` 等可读信号，完全靠"能不能创建成功"黑盒判断 |

## 四、给你的建议

1. **别一次性冲 100**：先用 10 的档测"创建成功率 + 实际处理时间"，再考虑提高。当前 10 并发已经有超时和队列阻塞。
2. **提高调度层容错**：POST 超时时重发（幂等需要你自己保证）；轮询超 10 分钟没开始处理就判失败并换策略。
3. **做任务落库**：把每个 `task_id`、创建时间、最后 status、最终 url / error 都落表，方便你事后看规律（比如周末 vs 工作日、不同时间段的等待时长）。
4. **多 key / 多供应商**：如果这是持续业务需求，建议同时准备 2–3 家视频生成供应商，把 Agnes 当作"便宜试错层"，主路径挂别的。
5. **再测一次更长观察窗**：下次跑 `观察窗=30~60 分钟`，看看这些 queued 的任务最终会不会出片；如果 30 分钟后还是 0，基本可以判定"免费用户 video 队列不可靠"。
