---
name: voice-to-video
description: >-
  Full-auto Google Flow Ultra & Gemini Veo cinematic voice-to-video and
  PPT/PDF-to-video pipeline for Google Antigravity. Converts spoken ideas,
  text prompts, or PPTX/PDF slide decks into storyboard scripts, locked subject
  consistency reference images, real dynamic AI video clips (zero-upload Google
  Flow in-site loop using Google AI Ultra 10,000 credits, or concurrent
  Gemini/Vertex Veo 3.1 API), free Chinese AI voiceover (edge-tts), and
  cinema-packaged 1080p 24fps MP4 with frosted chapter badges, rounded
  translucent pill subtitles, and storyboard contact-sheet QC.
---

# Voice-to-Video Full-Auto Cinema Skill (v2.2)

本 Skill 让 **Google Antigravity** 具备「**语音/文字一句话 → 分镜脚本 → 主体一致性锁脸 → 真·动态 AI 视频生成 → 中文 AI 配音与电影级字幕包装 → 抽帧自检**」的全自动电影级视频制作能力。

> **核心底线**：除非用户明确要求“只要静态图预览”，否则**绝不使用静态图推拉冒充最终成品**，必须通过 Google Flow 或已配置的视频 API 生成真正的动态 MP4 镜头后再合片。

---

## 0. 路径与环境自检（兼容全局安装与项目级安装）

本 Skill 目录记为 `<SKILL_DIR>`（即本 `SKILL.md` 所在目录，支持全局 `~/.gemini/config/skills/voice-to-video` 或项目内 `.agents/skills/voice-to-video`）。

选择 Python 解释器（优先 `<SKILL_DIR>/.venv/bin/python` 或当前工作区 `.venv/bin/python`，其次 `python3`）：
```bash
PY="$( [ -x "<SKILL_DIR>/.venv/bin/python" ] && echo "<SKILL_DIR>/.venv/bin/python" || ( [ -x ".venv/bin/python" ] && echo ".venv/bin/python" || echo "python3" ) )"
"$PY" "<SKILL_DIR>/scripts/check_env.py"
```

- 首次在全新电脑使用时，若缺少 `edge_tts` 或 `PIL`，直接运行一键初始化脚本（免费零 API 费）：
  ```bash
  bash "<SKILL_DIR>/scripts/setup.sh"
  ```
- 需要系统已安装 `ffmpeg`、`ffprobe` 与中文字体（如 Noto Sans CJK / PingFang / 微软雅黑）。

---

## Phase 1: 语音输入与极简需求定调

- 用户可通过 Antigravity **Voice Mode**（`F6` / `/voice live`）、**语音听写**（`F5` / `/voice dictate`）、文字描述、**PPT / PDF 演示文稿**，或直接提供录音素材下达视频需求。
- **若用户提供 `.pptx` 或 `.pdf` 演示文稿**，先运行零依赖解析脚本提取每页标题、要点、演讲者备注、内嵌图片（以及可选页面截图）：
  ```bash
  "$PY" "<SKILL_DIR>/scripts/parse_deck.py" \
    --input "<path/to/slides.pptx>" \
    --out-dir "<project_dir>/work/deck" \
    --render-slides
  ```
  解析后支持 **3 种 PPT 转视频模式**（按用户意图自动选定或简短确认）：
  1. **PPT → 电影级动态宣传片（默认推荐）**：提炼 PPT 核心叙事与备注讲稿，改写为口播文案 + 全片 `ai_video` 动态分镜，走 Google Flow / Veo 3.1 生成全片电影画面；
  2. **PPT 原页 + AI 动态混剪（适合路演/技术方案）**：数据图表/架构页用 `visual.type = "image"` 展示高清原页截图（配轻推镜头），场景/愿景页穿插 `ai_video` 动态镜头；
  3. **PPT 极速解说视频（零积分）**：全部页面用渲染出的 PPT 原页或 `card` + `edge-tts` 中文旁白 + 圆角字幕，30 秒零积分出片。
- 若提供录音或口播原片，先执行转写：
  ```bash
  "$PY" "<SKILL_DIR>/scripts/transcribe_audio.py" \
    --input "<project_dir>/input/<file>" \
    --out-dir "<project_dir>/work/transcript"
  ```
- 若用户未指定技术细节，默认采用电影级最佳实践（不打扰老板）：
  - 画幅与帧率：`16:9`（`1920x1080`，`24fps` 电影帧率）
  - 时长拆分：约 1 分钟 = **7 个动态镜头（每镜约 7.5~8.5 秒）+ 1 个 4 秒片尾大字卡**
  - 包装样式：左上角半透明章节角标（`PART 01 · ...`）+ 底部抗锯齿圆角黑底字幕条（`cinema_pill`）+ 深色径向渐变片尾卡（`outro_card`）
  - 省额度策略：常规镜头用 **Veo 3.1 Fast（Ultra 半价 10 积分/镜，x1）**，关闭视频模型自带音轨以省成本。

---

## Phase 2: 生成分镜脚本、视觉圣经与额度预估

在项目目录 `<project_dir>/`（如 `projects/<slug>/`）下创建 `script.md` 与 `script.json`（完整字段见 [references/script-template.md](./references/script-template.md)，示例见 [examples/sample-script.json](./examples/sample-script.json)）：
1. **`style_bible`**：统一英文电影画风圣经（光线、色温、场景基调、35mm 镜头质感）。
2. **`subjects`**：全片反复出现的角色/机器人/产品定妆描述（单镜最多引用 3 个主体）。
3. **`scenes`**：每镜设置 `chapter`、`narration`、`duration`、`visual.type = "ai_video"` 与完整英文 `video_prompt`；最后一镜设为 `outro_card`。

运行配音（免费中文 `edge-tts`，自动回写精准时长与同步 `output/subtitles.srt`）与积分/费用预估：
```bash
"$PY" "<SKILL_DIR>/scripts/generate_tts.py" --script "<project_dir>/script.json"
"$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --estimate-only
```
用 **3 行以内摘要**向用户汇报预计片长、镜头数和预计消耗的 Ultra 积分/费用。

---

## Phase 3: 真·动态 AI 视频生成（优先 Google Flow 站内全闭环，零额外 API 费用）

根据 `check_env.py` 报告的激活引擎自动选择以下路径之一：

### 路径 A（默认推荐 · 零额外费用）：Google Flow 站内全闭环（消耗 Google AI Ultra 10,000 月度积分）

> **关键经验**：浏览器安全策略会拦截本地文件上传至 Google 域名，因此最稳、100% 全自动的方式是**直接在 Google Flow 站内完成「图片定妆 → 素材转视频」闭环**，全程零本地上传！

1. 导出队列清单：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --provider google_flow
   ```
2. 拉起 Antigravity `browser` 子智能体（`Model="flash"`）访问 `https://flow.google.com`：
   - 若遇到 Google 登录页或人机验证，立即暂停提示用户在浏览器面板完成登录（**严禁绕过登录或验证码**），完成后通过 `send_message` 复用同一已登录标签页继续；
   - **Stage 1（站内锁主体定妆照）**：新建项目，在底部切换到 **「图片 (Image)」** 模式（16:9，x1），按 `subjects` 生成每个核心主体的定妆照（自动进入 Flow 站内「图片」素材库）；
   - **Stage 2（站内素材转真·动态视频）**：切换到 **「视频 → 素材 (Ingredients)」** 模式，配置 **Veo 3.1 - Fast · 16:9 · 720p · 8 秒 · x1（每镜仅 10 积分）**，按分镜从 Flow 站内「图片」库挂载对应主体参考图，批量提交全部动态提示词；
   - **Stage 3（下载归档）**：等待全部镜头渲染完成，下载 `720p 原始尺寸` MP4，复制归档到 `<project_dir>/work/generated_videos/scene_01.mp4`、`scene_02.mp4`...

### 路径 B（已配置 `GEMINI_API_KEY` / Vertex AI / 火山引擎 Seedance）：纯 API 并发调度

若用户已在 `.env` 配置 `GEMINI_API_KEY` 并希望走 API 后台并发（详见 [references/google-video-engines.md](./references/google-video-engines.md)）：
```bash
"$PY" "<SKILL_DIR>/scripts/prepare_subjects.py" --script "<project_dir>/script.json" --mode gemini_api --concurrency 4
"$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --provider auto --concurrency 4
```

---

## Phase 4: 电影级合片与视觉自检

1. 一键完成时长适配、左上角磨砂章节角标叠加、底部圆角半透明字幕条压制、深色片尾大字卡渲染与 BGM 混音：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/build_video.py" --script "<project_dir>/script.json"
   ```
2. **交付前必须执行视觉自检**：
   使用 `read_file` 查看 `<project_dir>/output/preview_frames/contact_sheet.jpg` 及代表性分镜帧，确认跨镜头角色一致、动态画面无严重畸变、章节角标与中文字幕清晰无截断。
3. **局部语音微调**：
   若用户对某一镜不满意，仅重新生成该镜并覆盖 `work/generated_videos/scene_XX.mp4`，重跑 `build_video.py` 即可 10 秒完成重新合片交付。
