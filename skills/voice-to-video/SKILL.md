---
name: voice-to-video
description: >-
  Full-auto Google Flow Ultra & Gemini Veo cinematic video production skill for
  Google Antigravity. Converts spoken ideas, text prompts, or PPTX/PDF slide
  decks into storyboard scripts, locked Flow Characters/Ingredients, real
  dynamic AI video clips (supporting Flow Extend/Save-frame continuity, Manual
  Mode, live credit reading, Checkpoint vs Full-Auto, and free 1080p or 4K
  upscaled exports), and clean 1080p/4K MP4 assembly. Subtitles, Chinese TTS
  voiceover, and chapter badges are strictly OPT-IN (off by default to preserve
  pure cinema visuals and native AI audio).
---

# Voice-to-Video Full-Auto Cinema Skill (v3.0)

本 Skill 让 **Google Antigravity** 具备从「**语音/文字想法或 PPT/PDF 演示文稿 → 分镜脚本 → Google Flow 深度制片（Characters / 素材 / Extend / 尾帧接续）→ 纯净 1080p/4K 电影成片（按需可选配音/字幕）→ 视觉自检**」的全流程视频制作能力。

> **两条铁律**：
> 1. **严禁用静态图推拉冒充动态成片**（除非用户明确只要静态预览）。
> 2. **默认输出纯净动态视频**：中文字幕、AI 中文配音、左上角磨砂章节角标、文字片尾卡**默认全部关闭**，保留 Veo 3.1 / Omni 1.2 Flash 原生现场声音与音乐；仅在用户明确要求（例如 PPT 演讲解说、知识科普）时才按需启用。

---

## 0. 路径与环境自检（兼容插件安装、全局与项目级安装）

本 Skill 目录记为 `<SKILL_DIR>`（即本 `SKILL.md` 所在目录）：
```bash
PY="$( [ -x "<SKILL_DIR>/.venv/bin/python" ] && echo "<SKILL_DIR>/.venv/bin/python" || ( [ -x ".venv/bin/python" ] && echo ".venv/bin/python" || echo "python3" ) )"
"$PY" "<SKILL_DIR>/scripts/check_env.py"
```
首次在全新电脑使用时，若缺少 `PIL`（或需要可选的 `edge_tts`），运行一键初始化：
```bash
bash "<SKILL_DIR>/scripts/setup.sh"
```

---

## Phase 1: 需求定调与清晰度二选一

- **清晰度二选一确认（未指定时必问，已移除 2K）**：
  如果用户下达任务时没有指定清晰度，正式生成前必须给出明确二选一：
  1. **`1080p`（推荐，默认）**：Google Flow 免费 `1080p` 超分（Ultra 1～10 秒 **+0 积分**），导出 `1920×1080`；
  2. **`4k`（`3840×2160`）**：Google Flow Ultra 专属 `4K` 超分（**+50 积分/镜**），原生 4K 导出。
- **纯净模式 vs 解说包装模式判断**：
  - **纯净动态片（默认）**：`tts.enabled = false`、`subtitles.enabled = false`、`chapter = ""`、`keep_audio = true`（保留 AI 原生音乐/现场环境音/对白），不硬塞黑底片尾卡。
  - **解说/汇报片（仅在用户明确要求配音/字幕/PPT 讲解时开启）**：按需开启 `tts.enabled = true`、`subtitles.enabled = true`（可选 `chapter` 章节角标）。
- **PPT / PDF 演示文稿输入**：
  若用户提供 `.pptx` 或 `.pdf`，先运行零依赖解析脚本提取每页标题、要点、表格、演讲者备注与内嵌图片：
  ```bash
  "$PY" "<SKILL_DIR>/scripts/parse_deck.py" \
    --input "<path/to/slides.pptx>" \
    --out-dir "<project_dir>/work/deck" \
    --render-slides
  ```
- **录音/口播输入**：先运行 `transcribe_audio.py` 提取逐字稿与时间戳。

---

## Phase 2: 分镜脚本与导演提示词策划

在 `<project_dir>/` 下创建 `script.md` 与 `script.json`（参考 [references/script-template.md](./references/script-template.md) 与 [references/veo-prompt-guide.md](./references/veo-prompt-guide.md)，默认纯净配置示例见 [examples/sample-script.json](./examples/sample-script.json)）：
1. 为每个视频定制契合题材的视觉语言（不要千篇一律套用“科技风暗场+霓虹雾”），在提示词里写清镜头语言、动作节拍与原生声景（ambient sound / music / foley）。
2. 如开启可选中文 AI 配音（仅当 `tts.enabled == true`），运行：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/generate_tts.py" --script "<project_dir>/script.json"
   ```
3. 运行预估脚本查看大致耗时与积分：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --estimate-only
   ```

---

## Phase 3: 真·动态 AI 视频生成（优先 Google Flow 站内全闭环）

### 路径 A（默认推荐 · 零额外 API 费用）：Google Flow Ultra 站内深度制片

完整高级技法详见同插件内的 **`flow-scene-continuity`** 技能，核心流程如下：
1. 直接通过 `browser` 子智能体（`Model: "flash"`）打开 **`https://flow.google.com/`**，按 `rules/AGENTS.md` 执行 **Fast-Path 登录态快检**（未登录或遇 CAPTCHA 立即暂停交由用户操作，严禁绕过）。
2. **切至手动模式**：新建项目后关闭 `Flow Agent` 开关（Manual Mode），避免 Flow 擅自改写提示词。
3. **主体一致建档**：
   - 优先使用 Flow 专用 **Characters**（`/project/<id>/character`）建档锁定主角；辅助道具/环境用站内 **`图片`（Nano Banana 2.1，x1）** 生成入库（零本地文件上传）。
4. **读取实时积分 & 模式分支**：
   - 配好 **`视频 → 素材 (Ingredients)`** 或 **`视频 → 帧 (Frames)`**（`Veo 3.1 - Fast` 或 `Omni 1.2 Flash`，`16:9`，`x1`），读取页面实时 **`Generating will use <N> credits`** 提示；
   - **`checkpoint` 模式（默认）**：汇报真实扣分等用户确认后再开跑；
   - **`auto` 模式**：用户指令含“全自动 / auto mode / 直接做”时自动连续执行。
5. **连续性优先**：
   - 需要连续长动作（如舞蹈、跟随行走）时，善用 Flow Clip Editor 的 **`Extend`（延长）** 或 **`Save frame`（抽尾帧接下一镜起始帧）**，减少碎片化硬切！
6. **按选定清晰度下载归档**：
   - 选 `1080p`（默认）：下载 Flow 免费 **`1080p` 超分版 MP4（+0 积分）**；
   - 选 `4k`：下载 Flow **`4K` 超分版 MP4（+50 积分/镜）**；
   - 归档为 `<project_dir>/work/generated_videos/scene_01.mp4`、`scene_02.mp4`...

### 路径 B（已配 API Key）：纯 API 后台并发

若 `.env` 已配置 `GEMINI_API_KEY` / Vertex AI / `VOLCENGINE_API_KEY`（详见 [references/google-video-engines.md](./references/google-video-engines.md)）：
```bash
"$PY" "<SKILL_DIR>/scripts/prepare_subjects.py" --script "<project_dir>/script.json" --mode gemini_api --concurrency 4
"$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --provider auto --concurrency 4
```

---

## Phase 4: 1080p / 4K 合片与 Contact Sheet 视觉自检

1. 按用户选定清晰度合片（默认纯净无字幕、无角标、保留原生视频音轨；若开启了可选配音/字幕/BGM 则自动混音压制）：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/build_video.py" \
     --script "<project_dir>/script.json" \
     --resolution 1080p   # 或 4k
   ```
2. **交付前必做视觉自检**：
   用 `read_file` 查看 `<project_dir>/output/preview_frames/contact_sheet.jpg` 及重点分镜帧，核验人物一致性、动作流畅度与画面干净度；若单镜有瑕疵，仅在 Flow 重拍或 Inline Edit 该镜后 10 秒重新合片。
