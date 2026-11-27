# Antigravity Voice-to-Video & Google Flow Plugin (v3.2)

[![Antigravity Plugin](https://img.shields.io/badge/Google%20Antigravity-Plugin-4285F4?logo=google&logoColor=white)](https://antigravity.google)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

面向 **Google Antigravity** 的全自动电影级视频制作插件：整合了 **Google Flow 站内深度制片**（默认 `Omni 1.2 Flash` 15 秒长镜头、参考图角色锁定 + 背景光影覆盖法、Characters 角色建档、Extend 延长、Save frame 尾帧接续、Manual Mode、实时积分读取、Checkpoint / Full-Auto 双模式、`/flow-sync` 零积分界面巡检）以及 **参考视频分镜拆解 & 原音轨无损直贴（`prep_v2v_segments.py` + `replace_audio: true`）、PPT/PDF 读稿、可选中文 AI 配音/字幕、1080p/4K 本地合片与 Contact Sheet 质检**。

---

## 核心设计原则（v3.2 `Omni 1.2 Flash` 15s 长镜头 + 参考视频翻拍工作流）

- **参考视频 / 音乐 MV 复刻管线（v3.2 新增）**：
  - **`prep_v2v_segments.py`**：一键对本地参考视频提取完整无损原音轨（`master_audio.m4a`）、切段（默认 `-an` 无声切片）并自动生成全片视觉分镜接触表（`work/storyboard_ref/sheet_*.jpg`），Agent 逐段审图复刻真实光影色彩、人数队形与运镜节奏；
  - **`build_video.py` `bgm.replace_audio: true`**：完整不间断原音轨直贴成片，零混音衰减与失真；
  - **背景与光影强制覆盖法**：单张锁定角色参考图即可实现 100% 主体一致性 + 跨多场景高反差电影光影切换（紫霓虹走廊 / 霓虹楼梯 / 高空俯拍圆形聚光灯 / 暖金大舞室）。
- **Google Flow 模型更新与实测避坑（2026-11 实测）**：
  - 默认切换至 **`Omni 1.2 Flash`（最长 `15 秒` 单次直出 + `1080p` 高清重塑仅 +5 积分/15s，`<=10s` 免费）**，提前规避 `Veo 3.1 Fast / Quality` 与 `Omni 1.1 Flash` 于 2026-12-05 停用；
  - 内置 **时长重置防呆**（Flow 每次提交后自动复位 8 秒）与 **Flow 网页端 `p=speech_edit` 边界说明**（跳过无效的真人视频上传 V2V，直接走分镜拆解 + 纯参考图 15 秒长镜头）。
- **反模板化导演引擎（`director-playbooks.md`）**：
  - **开拍前 10 秒定调卡**：宽泛需求先一次性对齐「3 个反差视觉方向」与「1080p / 4K 画质」，告别 Agent 瞎猜套壳；
  - **4 类通用题材分流**（剧情微电影 / 写实真机纪录 / 节奏表演混剪 / PPT 商业解说）+ **反 AI 塑料味黑名单**（禁止无关霓虹雾、发光胸环与连续 3 镜重复运镜）。
- **默认纯净动态成片**：默认**关闭**中文字幕、AI 中文配音与左上角磨砂章节角标，原生保留 **Omni 1.2 Flash** / Veo 的电影声景或完整原曲音轨；仅在用户明确需要解说/字幕（如 PPT 讲解）时按需开启。
- **通用非线性时间线剪辑（`build_video.py`）**：支持同一段 Flow 素材按 `start`/`end`/`duration` 多段截取与 A/B-roll 交叉复用、支持每镜独立配置 `cut`/`dissolve`/`fadeblack` 转场、完整原音轨直贴（`replace_audio: true`）与无断层音频过渡（`acrossfade`），支持原生 **1080p / 4K** 导出（已移除 2K）。
- **Google Flow 深度操控**：
  - 直连 `https://flow.google.com/` + Fast-Path 登录态快检 + 自动关闭 `Flow Agent`（Manual Mode 防改提示词）；
  - 支持专用 **Characters**（`/character`）、**`Extend` 延长镜头**、**`Save frame` 尾帧接下一镜**与在线局部修改；
  - 读取页面实时 `Generating will use <N> credits` 扣分提示，支持 **Checkpoint（默认确认）** 与 **Full-Auto（全自动）** 两种自治模式；
  - 内置只读 0 积分 `/flow-sync` 技能，Flow 改版时一键巡检并修复 UI 漂移。
- **多输入 + 多引擎扩展**：支持语音/文字直接策划、**本地参考视频/MV 拆解（`prep_v2v_segments.py`）**、**PPTX/PDF 零依赖读稿（`parse_deck.py`）**，并保留 Gemini Veo 3.1 API / Vertex AI / 火山引擎即梦 Seedance API 并发后端。

---

## 快速安装

### 方式 A：标准 Antigravity Plugin 一键安装（推荐）

```bash
agy plugin install https://github.com/topsun-bot/antigravity-voice-to-video-skill
```

### 方式 B：手动克隆到全局插件目录

```bash
git clone https://github.com/topsun-bot/antigravity-voice-to-video-skill.git \
  ~/.gemini/config/plugins/antigravity-voice-to-video-skill
```

### 初始化本地依赖（需系统已安装 `ffmpeg`）

```bash
bash ~/.gemini/config/plugins/antigravity-voice-to-video-skill/skills/voice-to-video/scripts/setup.sh
```

---

## 插件结构

```text
.
├── plugin.json                            # 标准 Antigravity Plugin 清单
├── rules/
│   └── AGENTS.md                          # 全局运营规则（纯净默认 / 1080p-4K / Fast-Path / Checkpoint-Auto）
├── skills/
│   ├── voice-to-video/                    # 主制片流水线（语音/PPT -> 脚本 -> Flow/API -> 1080p/4K合片）
│   │   ├── SKILL.md
│   │   ├── examples/sample-script.json
│   │   ├── references/
│   │   │   ├── veo-prompt-guide.md        # Veo 3.1 / Omni 1.2 Flash 导演提示词与声景指南
│   │   │   ├── script-template.md
│   │   │   ├── google-video-engines.md
│   │   │   └── editing-backends.md
│   │   └── scripts/                       # build_video.py / parse_deck.py / generate_videos.py / ...
│   ├── flow-scene-continuity/             # Flow 高级连续制片（Characters / Extend / Save frame / Inline Edit）
│   │   └── SKILL.md
│   └── flow-sync/                         # 手动触发 /flow-sync：零积分只读巡检 Flow 界面改版
│       ├── SKILL.md
│       └── references/audit-checklist.md
├── .env.example
└── LICENSE
```

## License

[MIT](./LICENSE)
