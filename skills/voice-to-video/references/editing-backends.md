# 视频制作与剪辑后端扩展指南

本工作流默认使用 **内置本地 FFmpeg + Pillow 卡片流水线**（零外部 API 依赖、离线可用、跨平台稳定）。当你有更高级的视觉或人工精修需求时，可以将 Phase 4 替换为以下任意后端，或与本工作流组合使用：

---

## 方案 1：Remotion 动效后端（代码级高级动画 / 产品宣传片）
适合：SaaS 产品演示、数据可视化、炫酷排版动画、代码逐行高亮动画。

- **开源参考仓库**：
  - `luminexlabs-io/antigravity-remotion-skill`（面向 Antigravity 的 Remotion Skill）
  - `remotion-dev/skills`（Remotion 官方 Agent Skill，可通过 `npx skills add remotion-dev/skills` 引入）
- **集成方式**：
  1. 沿用本工作流的 Phase 1~3（语音输入 → `script.json` → `generate_tts.py` 产出音频与精准每幕时长）。
  2. 将 `script.json` 作为 `inputProps` 传给 Remotion React 组件。
  3. 使用 `npx remotion render` 渲染最终 MP4。

---

## 方案 2：剪映（JianYing）草稿后端（中文生态 / 人工二次精修）
适合：抖音/B站/小红书创作者，希望 AI 完成 80% 粗剪和字幕，最后自己在剪映里挑特效、贴纸和花字。

- **开源参考仓库**：
  - `harveyzhang/jianying-editor-skill`（Antigravity 剪映自动化 Skill，底层通常基于 `pyJianYingDraft`）
- **集成方式**：
  1. 沿用 Phase 1~2 生成 `script.json` 与配音文件。
  2. 通过 `pyJianYingDraft` 脚本将 `script.json` 的每个分镜、字幕和配音写入剪映本地草稿目录。
  3. 打开剪映客户端微调后导出。

---

## 方案 3：MCP 专业时间线编辑器（Final Cut Pro / DaVinci / Premiere）
适合：专业剪辑师，需要导出 `.fcpxml` 或驱动本地无头视频引擎。

- **开源参考仓库**：
  - `MakeMyClip/editor`（本地 FFmpeg + `whisper.cpp` + MCP Server，支持基于文本剪辑与 `.fcpxml` 导出）
  - `kajisho5/ffmpeg-skill`（40+ 原子化 FFmpeg MCP 工具集）

---

## 方案 4：Antigravity Marketplace 插件组合（云端 AI 生成 + 时间线编辑）
适合：需要文生视频素材、AI 音乐、或可视化云端时间线剪辑。

- **`invideo` 插件**：直接连接 AI 原生时间线编辑器，边对话边完成裁切、调色和混音。
- **`gemini-api` 插件**：调用 Gemini 多模态能力生成配图、Veo 视频片段、语音合成（TTS）与背景音乐，将生成的素材保存到 `projects/<slug>/input/` 后再由 `build_video.py` 统一合成。
