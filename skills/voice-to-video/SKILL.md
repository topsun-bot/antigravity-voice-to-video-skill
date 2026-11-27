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

# Voice-to-Video Full-Auto Cinema Skill (v3.3)

本 Skill 让 **Google Antigravity** 具备从「**语音/文字想法、本地参考视频/MV 或 PPT/PDF 演示文稿 → 分镜脚本 → 独立只读审核防抽卡 → Google Flow 深度制片（`Omni 1.2 Flash` 15 秒长镜头 / 资产三件套 / 背景光影覆盖 / 先尾后首关键帧 / Extend）→ 纯净 1080p/4K 电影成片（支持 `replace_audio` 原音轨直贴、按需可选配音/字幕）→ 全片与切点 `±3 帧` 视觉自检**」的全流程视频制作能力。

> **两条铁律**：
> 1. **严禁用静态图推拉冒充动态成片**（除非用户明确只要静态预览）。
> 2. **默认输出纯净动态视频**：中文字幕、AI 中文配音、左上角磨砂章节角标、文字片尾卡**默认全部关闭**，保留 **Omni 1.2 Flash** / Veo 原生现场声音（或在复刻参考视频/MV 时直贴完整原音轨 `bgm.replace_audio: true`）；仅在用户明确要求（例如 PPT 演讲解说、知识科普）时才按需启用。

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

## Phase 1: 题材分流、10 秒定调卡与清晰度二选一

先读取 [references/director-playbooks.md](./references/director-playbooks.md) 确定本片所属题材语法（剧情短片 / 写实真机纪录 / 节奏表演混剪 / PPT 商业解说）：
- **开拍前「10 秒导演定调卡」（宽泛需求必做）+ 清晰度二选一（已移除 2K）**：
  - 若用户只给了宽泛主题（无具体脚本或 PPT），用一次 `ask_question` 同时确认：
    1. **3 个反差极大的视觉方向**（按题材定制，绝不套旧模板）；
    2. **导出清晰度二选一**：**`1080p`（推荐，Flow 免费超分 +0 积分）** / **`4k`（3840×2160，Flow Ultra 专属 4K 超分 +50 积分/镜）**。
  - 若用户已提供完整脚本或 PPT/PDF，则跳过方向题，仅在未指定画质时询问 `1080p` / `4k`。
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
- **本地参考视频 / 舞蹈 MV 复刻输入（v3.2 新增）**：
  若用户提供本地 `.mp4` 参考视频要求按其编舞、节奏、机位或原曲翻拍（如真人舞蹈改机器人舞团、风格重塑），**不要上传真人视频进 Flow 网页端**（Flow 网页端会触发 `p=speech_edit` 拦截），改为一条命令在本地自动抽全片原音轨 + 切段 + 生成分镜接触表：
  ```bash
  "$PY" "<SKILL_DIR>/scripts/prep_v2v_segments.py" \
    --input "<path/to/reference.mp4>" \
    --project-dir "<project_dir>" \
    --chunk-seconds 15 \
    --resolution 1080p
  ```
  随后用 `read_file` 逐张审阅生成的 `<project_dir>/work/storyboard_ref/sheet_*.jpg`，精准记录每 15 秒的真实场景光影、人数队形变化与机位运动，写入 `<project_dir>/script.json`（已自动配好 `bgm.replace_audio: true` 与 `input/master_audio.m4a`）。
- **录音/口播输入**：先运行 `transcribe_audio.py` 提取逐字稿与时间戳。

---

## Phase 2: 分镜脚本、导演提示词策划与「独立只读审核关卡」（防抽卡）

在 `<project_dir>/` 下创建 `script.md` 与 `script.json`（参考 [references/script-template.md](./references/script-template.md)、[references/director-playbooks.md](./references/director-playbooks.md) 与 [references/veo-prompt-guide.md](./references/veo-prompt-guide.md)，默认纯净配置示例见 [examples/sample-script.json](./examples/sample-script.json)）：
1. 为每个视频定制契合题材的视觉语言（黄金分割 38%/62% 构图、不连续 3 镜同景别/同运镜、剧情群演错峰反应），在提示词里写清 `【站位】` 空间左右、6 要素镜头语言、逐秒动作节拍与原生声景，并对照 16 条 AI 穿帮清单自排雷。
2. **提交视频生成前的独立只读审核（v3.3 新增，强烈推荐用于 >=4 镜的多镜头项目）**：
   - 遵循「能在文字阶段拦截的错绝不画图，能在图片阶段拦截的错绝不烧视频积分」原则：
   - 拉起一个**全新的只读 `research` 子智能体**（只传 `script.json` 路径，避免主 Agent 确认偏差），专项核查：
     - 跨镜角色服装/道具/左右站位是否矛盾；
     - 是否误入版权/品牌/艺人敏感词或触发 Flow `p=speech_edit`；
     - 是否存在单镜塞 3 个大动作、负面提示词反触发、连续 3 镜相同运镜或时长总和与音频不匹配；
   - 审核输出明确 **`通过`**（或修完所有阻断项）后，再进入 Phase 3 花积分生视频。
3. 如开启可选中文 AI 配音（仅当 `tts.enabled == true`），运行：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/generate_tts.py" --script "<project_dir>/script.json"
   ```
4. 运行预估脚本查看大致耗时与积分：
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
4. **首选模型、实时积分读取 & 防呆校验**：
   - 配好 **`视频 → 素材 (Ingredients)`** 或 **`视频 → 帧 (Frames)`**，默认首选 **`Omni 1.2 Flash`**（`16:9`，`720p`，`x1`，支持 **`3–15 秒`** 单次长镜头；注：`Veo 3.1 Fast / Quality` 与 `Omni 1.1 Flash` 将于 2026-12-05 停用，低成本备选为 `Veo 3.1 - Lite`）；
   - **时长重置防呆**：Flow 每次提交后会把时长自动重置回 `8 秒`，提交非 8 秒片段（如 `15 秒` / `9 秒`）前必须逐镜二次确认时长；
   - **背景与光影强制覆盖**：单张参考图跨多场景使用时，提示词必须显式声明 `"matching ONLY the character design from the reference image; completely ignore the reference image's background and flood the scene with [目标光影/场景/机位]"`；
   - 读取页面实时 **`Generating will use <N> credits`**（或中文扣分提示）：`checkpoint` 模式（默认）向用户汇报真实扣分确认后再开跑；`auto` 模式连续执行（大项目建议每 5 镜分批生成并抽帧质检）。
5. **连续性优先**：
   - 优先利用 `Omni 1.2 Flash` 的 **15 秒单次长镜头**，并在需要更长连续动作时结合 **`Extend`（延长，最高 30s）** 或 **`Save frame`（抽尾帧接下一镜起始帧）**，减少碎片化硬切！
6. **按选定清晰度下载归档**：
   - 选 `1080p`（默认）：下载 **`1080p 已高清重塑`**（1–10s 免费 +0 积分，11–15s 仅 +5 积分/镜）；
   - 选 `4k`：下载 **`4K` 超分版 MP4（+50 积分/镜）**；
   - 逐个下载并精确记录映射，归档为 `<project_dir>/work/generated_videos/scene_01.mp4`（或 `seg_01.mp4`）...

### 路径 B（已配 API Key）：纯 API 后台并发

若 `.env` 已配置 `GEMINI_API_KEY` / Vertex AI / `VOLCENGINE_API_KEY`（详见 [references/google-video-engines.md](./references/google-video-engines.md)）：
```bash
"$PY" "<SKILL_DIR>/scripts/prepare_subjects.py" --script "<project_dir>/script.json" --mode gemini_api --concurrency 4
"$PY" "<SKILL_DIR>/scripts/generate_videos.py" --script "<project_dir>/script.json" --provider auto --concurrency 4
```

---

## Phase 4: 通用非线性时间线合片（1080p / 4K）与视觉自检

1. `build_video.py` 支持**多片段自由截取与素材复用**（同一段 Flow 素材可通过 `visual.start` + `duration` / `visual.end` 被多个镜头交叉剪辑）、可选播放倍速（`visual.speed`）、每镜独立转场（`transition`: `cut` / `dissolve` / `fadeblack` / `smoothleft` + `transition_duration`）、**完整原音轨无损直贴（`bgm.replace_audio: true`）**与**无断层音频交叉淡化（`acrossfade` / 防爆音微淡入淡出）**。执行合片：
   ```bash
   "$PY" "<SKILL_DIR>/scripts/build_video.py" \
     --script "<project_dir>/script.json" \
     --resolution 1080p   # 或 4k
   ```
2. **交付前必做双表视觉自检（`contact_sheet.jpg` + 切点 `±3 帧` `cuts_qc.jpg`）**：
   - `build_video.py` 会自动输出两张质检图：
     1. `<project_dir>/output/preview_frames/contact_sheet.jpg`（每镜中点总览，核验人物一致性、动作流畅度与画面干净度）；
     2. `<project_dir>/output/preview_frames/cuts_qc.jpg`（**每个转场切点前后 `-3f / -1f | +1f / +3f` 精检表**，中间红线标出精确切点，一眼抓跳切、闪黑、鬼影与色偏）。
   - 用 `read_file` 查看两张质检图（多镜头关键项目可交由只读 `research` 子智能体独立复核）。
   - **能剪就剪、最后才重抽**：若仅某镜首尾 0.3–1s 穿帮，优先在 `script.json` 调 `visual.start` / `duration` 裁掉坏帧重拼（10 秒出片、0 积分）；确需重拍时仅重拍单镜并保留旧版备份，避免盲目整批重抽。
