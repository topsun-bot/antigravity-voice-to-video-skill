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

## 通道 2：Google Flow + Google AI Ultra（月度 10,000 积分池，性价比之王）

适合：**充分利用 Google AI Ultra 账号自带的 10,000 Flow 月度积分**（0 额外 API 费用）。

- **2026-11 实测可用模型与退场提醒**：
  - **首选 `Omni 1.2 Flash`**：支持 `3–15 秒` 单次直出长镜头（`720p · 8s` 约 24 积分，`720p · 15s` 约 60 积分；`1080p` 高清重塑 `<=10s` 免费，`11–15s` 仅 +5 积分）。
  - **低成本备选 `Veo 3.1 - Lite`**：适合纯基础动态镜头的省积分方案。
  - **旧模型停用**：`Veo 3.1 - Fast`、`Veo 3.1 - Quality`、`Omni 1.1 Flash` 将于 **2026 年 12 月 5 日停用**，新项目请勿再设为默认。
- **Flow 网页端实测避坑**：
  - 严禁上传真人视频在 Flow 网页端走 V2V 换人（强触发 `p=speech_edit` / `音频生成失败`）；复刻参考视频请走本地 `prep_v2v_segments.py` 抽分镜接触表 + Flow 纯角色参考图 `15 秒` 长镜头 + `build_video.py` `replace_audio: true` 原音轨直贴。
  - Flow 每次提交后时长会自动重置回 `8 秒`，每次提交 `15 秒` 前必须逐镜确认。
- **执行方式**：
  1. 在已登录 Google AI Ultra 账号的浏览器（Antigravity `browser` 子智能体）中直接打开 `https://flow.google.com/`，在站内用 `Nano Banana 2.1`（`x1`）生成锁定角色参考图；
  2. 将下载好的 1080p/4K 镜头按顺序归档为 `projects/<slug>/work/generated_videos/scene_01.mp4`（或 `seg_01.mp4`）...
  3. 运行 `build_video.py --script projects/<slug>/script.json --resolution 1080p`，自动完成原音轨直贴（或可选配音/字幕）与 1080p/4K 成片合成。

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
