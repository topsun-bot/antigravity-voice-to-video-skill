# Google 生态视频引擎接入与成本控制指南

本工作流默认**优先使用 Google 账号自带的视频与图像能力**，支持以下三条通道无缝切换：

---

## 通道 1：Google Gemini API（Veo 3.1 + Gemini Image，全自动并发首选）

适合：**给老板做 100% 无人值守全自动出片**，不碰浏览器、不卡排队、支持 `ThreadPoolExecutor` 并发提交与断点续跑。

1. 在 Google AI Studio (`https://aistudio.google.com/apikey`) 获取 API Key。
2. 在工作区根目录复制 `.env.example` 为 `.env` 并填入：
   ```bash
   GEMINI_API_KEY=你的_API_KEY
   GOOGLE_VIDEO_BACKEND=auto
   MAX_CONCURRENCY=4
   VIDEO_ENABLE_AUDIO=false
   ```
3. **主体一致性实现原理**：
   - `generate_videos.py` 会自动读取每个分镜的 `visual.subjects`（最多 3 个），将锁定好的 `assets/subjects/*.png` 编码写入 Veo 3.1 `predictLongRunning` 接口的 `referenceImages`（`referenceType: "asset"`）字段。
   - 若该分镜未指定主体或为竖屏 `9:16`，则自动挂载 `visual.first_frame` 作为首帧图生视频（Image-to-Video）条件。
4. **费用优化**：
   - 常规分镜在 `script.json` 中设为 `"tier": "fast"`（`veo-3.1-fast-generate-preview`），开场/核心大特写设为 `"tier": "quality"`（`veo-3.1-generate-preview`）。
   - 解说片关闭视频自带音效（`VIDEO_ENABLE_AUDIO=false`），可省 30%–50% 成本。

---

## 通道 2：Google Flow + Google AI Ultra（\$99.99/月 10,000 积分池，性价比之王）

适合：**充分利用老板 \$99.99/月 Google AI Ultra 账号自带的 10,000 Flow 积分**（Ultra 享 Veo Lite 5 积分/镜、Veo Fast 10 积分/镜半价优惠，同等预算产出是纯 API 现付的 5 倍以上）。

1. 当未配置 `GEMINI_API_KEY` 时，运行 `generate_videos.py --provider google_flow` 会自动生成：
   - `work/google_flow_queue.json`（机器可读批量队列）
   - `work/google_flow_prompts.md`（带参考图路径与档位建议的清单）
2. 执行方式：
   - 在已登录老板 Google AI Ultra 账号的浏览器（或 Antigravity `browser` 子智能体）中打开 `https://flow.google.com`，上传对应 `assets/subjects/*.png` 主体图并生成每个镜头；
   - 将下载好的镜头保存为 `projects/<slug>/work/generated_videos/scene_01.mp4`、`scene_02.mp4`...
   - 运行 `build_video.py --script projects/<slug>/script.json`，系统自动识别已下载镜头并完成配音、章节角标、圆角字幕和成片合成。

---

## 通道 3：Google Cloud Vertex AI（企业对公结算）

适合：公司已有 GCP 结算账号或企业赠金。
```bash
gcloud auth login
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```
`generate_videos.py` 会自动检测 `gcloud` 鉴权并切换到 Vertex AI Veo 3.1 端点。

---

## 备用非 Google 引擎（按需扩展）

- **国内即梦 / 火山方舟 Seedance API**：在 `.env` 中填入 `VOLCENGINE_API_KEY`，运行 `--provider volcengine_seedance` 即可全自动并发生成。
- **可灵 Kling AI / Runway**：推荐在 Antigravity 插件市场安装官方 `Kling AI` 插件（支持 V4 与可复用主体 Subject），或在 `generate_videos.py` 扩展对应 REST 适配器。
