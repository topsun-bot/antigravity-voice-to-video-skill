# Antigravity Voice-to-Video Skill

[![Antigravity Skill](https://img.shields.io/badge/Google%20Antigravity-Skill-4285F4?logo=google&logoColor=white)](https://antigravity.google)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

一套面向 **Google Antigravity** 的「**一句话语音/文字 → 分镜脚本 → 主体一致性锁脸 → 真·动态 AI 视频生成 → 中文 AI 配音与电影级包装合片**」全自动 Skill 工作流。

默认采用 **Google Flow 站内全闭环（零额外 API 费用）**：直接利用 Google AI Ultra 账号自带的月度 10,000 Flow 积分，自动在站内锁定主角/机器人定妆照、批量生成 8 秒 24fps **Veo 3.1** 真实动态镜头，并自动配上免费中文 AI 旁白、左上角磨砂章节角标、底部抗锯齿圆角字幕条与极简电影片尾大字卡。同时也原生支持 **Google Gemini API (Veo 3.1)**、**Vertex AI** 与**火山引擎即梦 Seedance API** 并发调用。

```text
[1. 语音/文字一句话]      [2. 脚本 + 视觉圣经]      [3. 主体一致性锁脸]          [4. 真·动态 AI 视频生成]          [5. 电影级包装合片 + 自检]
Voice Mode / 听写         script.md / script.json   Google Flow 站内「图片」     Flow「视频 → 素材」Veo 3.1 Fast   免费 edge-tts 中文配音 + BGM
或本地录音转写         →  + Ultra 积分/费用预估   →  锁定主角/机器人/道具外貌   →  挂载参考图批量出 8s 24fps MP4  →  磨砂章节角标 + 圆角黑底字幕
                                                                                 (或 Gemini/Vertex/Seedance API)   片尾大字卡 + Contact Sheet
```

---

## 核心特性

- **零额外 API 费用全自动闭环（默认免费 1080p 超分）**：支持直接在 Google Flow 站内完成「图片定妆 → 素材转视频 → **免费 1080p 超分下载（+0 积分）**」，充分利用 Google AI Ultra 月度 10,000 积分（1 分钟 7 镜头仅需约 **70 积分**，占月度额度 0.7%）。
- **支持 `1080p` / `2k` / `4k` 三档导出与自动询问**：未指定画质时自动弹出 `1080p`（免费超分）/ `2k`（2560×1440）/ `4k`（3840×2160）三选一；`build_video.py --resolution 1080p|2k|4k` 自动等比缩放圆角字幕与磨砂章节角标。
- **原生支持 PPT / PDF 读稿转视频（`parse_deck.py`）**：零额外 Python 依赖直接解析 `.pptx` 每页文字、表格、演讲者备注与内嵌图片（配合 `libreoffice`/`pdftoppm` 还可导原页高清截图），支持「PPT 转电影级动态宣传片」「原页+AI动态混剪」「零积分 PPT 解说视频」三种模式。
- **跨镜头主体一致性锁定**：通过 `style_bible`（全局视觉圣经）+ `subjects`（角色/产品定妆档案库），解决 AI 视频跨镜头“换脸/换衣服”问题。
- **多引擎无缝切换**：
  - **优先级 1（零额外费用）**：Google Flow Ultra 站内闭环（Veo 3.1 Fast / Lite / Quality）
  - **优先级 2（纯 API 后台并发）**：Google Gemini API (`veo-3.1-*-generate-preview:predictLongRunning`，自动挂载最多 3 张 `referenceImages`) / Vertex AI / 火山引擎即梦 Seedance API
- **电影级成片包装**：
  - 左上角半透明磨砂章节角标（如 `● PART 01 · 清晨照料与阳台浇花`）
  - 底部 2x 超采样抗锯齿圆角半透明字幕条（`cinema_pill`）
  - 深色径向渐变电影片尾大字卡（`outro_card`）
  - 渲染后自动生成全片 `contact_sheet.jpg` 供 Agent 视觉自检，不满意支持语音单镜局部重跑。

---

## 快速安装

### 1. 安装 Skill 到 Antigravity（任选全局或单项目）

**方式 A：全局安装（推荐，所有项目通用）**
```bash
git clone https://github.com/topsun-bot/antigravity-voice-to-video-skill.git /tmp/agy-v2v
mkdir -p ~/.gemini/config/skills
cp -r /tmp/agy-v2v/voice-to-video ~/.gemini/config/skills/voice-to-video
rm -rf /tmp/agy-v2v
```

**方式 B：安装到单个项目工作区**
```bash
mkdir -p .agents/skills
git clone https://github.com/topsun-bot/antigravity-voice-to-video-skill.git /tmp/agy-v2v
cp -r /tmp/agy-v2v/voice-to-video .agents/skills/voice-to-video
rm -rf /tmp/agy-v2v
```

### 2. 一键初始化本地依赖

确保系统已安装 `ffmpeg`（macOS：`brew install ffmpeg`；Ubuntu：`sudo apt-get install -y ffmpeg fonts-noto-cjk`），然后运行：
```bash
bash ~/.gemini/config/skills/voice-to-video/scripts/setup.sh
```
该脚本会自动创建 `.venv` 并安装免费中文 AI 配音库 `edge-tts` 与图像处理库 `Pillow`。

---

## 使用方式

在 Google Antigravity 中直接用 **Voice Mode（实时语音）**、**语音听写** 或 **打字** 提出视频想法，例如：

> “帮我生成一个一分钟的视频，机器人在家里完成了浇花、叠衣服的工作后，陪小孩玩耍”

Antigravity 会自动加载 `voice-to-video` Skill 并依次完成：
1. 生成分镜脚本 `script.md` / `script.json` 与免费中文 AI 配音（`edge-tts`），并汇报预计消耗的 Flow Ultra 积分；
2. 打开内置浏览器进入 `https://flow.google.com`（首次使用只需在浏览器面板点一下登录你的 Google AI Ultra 账号）；
3. 自动在 Flow 站内锁定主体参考图 → 批量生成 8 秒 24fps 真·动态 Veo 3.1 视频 → 下载并合成带章节角标与圆角字幕的 1080p `final.mp4`；
4. 输出 `contact_sheet.jpg` 视觉自检图，不满意任意镜头可直接开口要求局部重跑。

---

## 可选：切换为纯 API 后台并发模式

如果团队希望不经过浏览器、直接走按量付费 API 并发渲染，在工作区根目录复制 `.env.example` 为 `.env` 并填入对应 Key：
- **Google Gemini API (Veo 3.1)**：填入 `GEMINI_API_KEY`（设置 `GOOGLE_VIDEO_BACKEND=auto`）
- **Google Cloud Vertex AI**：填入 `GOOGLE_CLOUD_PROJECT` 并执行 `gcloud auth login`
- **国内火山引擎即梦 (Seedance)**：填入 `VOLCENGINE_API_KEY`

详见 [voice-to-video/references/google-video-engines.md](./voice-to-video/references/google-video-engines.md)。

---

## 仓库结构

```text
.
├── README.md
├── .env.example
├── LICENSE
└── voice-to-video/                   # Antigravity Skill 核心目录
    ├── SKILL.md                      # Skill 主入口与全自动 SOP
    ├── INSTALL_README.md             # 精简安装说明
    ├── examples/
    │   └── sample-script.json        # v2.2 电影级脚本示例
    ├── references/
    │   ├── script-template.md        # script.json 完整字段规范
    │   ├── google-video-engines.md   # Google Flow Ultra / Veo API / 备用引擎指南
    │   └── editing-backends.md       # Remotion / 剪映等扩展剪辑后端指南
    └── scripts/
        ├── setup.sh                  # 一键环境与依赖初始化脚本
        ├── check_env.py              # 环境与激活视频引擎检测
        ├── parse_deck.py             # PPTX / PDF 内容、讲稿备注与内嵌图片提取
        ├── transcribe_audio.py       # 本地音频/口播素材转写 (Whisper)
        ├── prepare_subjects.py       # 主体一致性参考图与首帧清单
        ├── generate_tts.py           # 免费中文 AI 配音与同步 SRT 字幕
        ├── generate_videos.py        # Google 优先多引擎并发调度与 Flow 队列导出
        ├── stage_flow_uploads.py     # 浏览器上传素材暂存助手
        ├── render_overlays.py        # 磨砂章节角标 / 圆角字幕条 / 电影片尾卡渲染
        ├── render_slide_card.py      # 信息卡片渲染器
        ├── build_video.py            # FFmpeg 电影级合片与 Contact Sheet 质检
        └── run_pipeline.py           # 一键 5 步总控入口
```

## License

[MIT](./LICENSE)
