# Voice-to-Video Antigravity Skill — 安装与使用说明

这套 Skill 可以让 **Google Antigravity** 通过一句话（语音或文字）全自动生成 **1080p 24fps 电影级真·动态 AI 视频**（含角色一致性锁定、免费中文 AI 配音、左上角磨砂章节角标、底部圆角字幕条与片尾大字卡）。

## 1. 10 秒安装（任选一种）

- **全局安装（推荐，所有项目通用）**：
  将本 `voice-to-video` 文件夹解压放到：
  ```text
  ~/.gemini/config/skills/voice-to-video/
  ```
- **单项目安装**：
  将本 `voice-to-video` 文件夹放到某个工作区下：
  ```text
  <你的项目目录>/.agents/skills/voice-to-video/
  ```

## 2. 一次性环境准备（免费配音 + 剪辑依赖）

1. 确保电脑已安装 `ffmpeg`（macOS：`brew install ffmpeg`；Ubuntu：`sudo apt-get install -y ffmpeg fonts-noto-cjk`）。
2. 运行初始化脚本安装免费中文配音（`edge-tts`）和图像处理（`Pillow`）：
   ```bash
   bash ~/.gemini/config/skills/voice-to-video/scripts/setup.sh
   ```

## 3. 直接开始用

在 Antigravity 里用语音或打字直接说：
> “帮我生成一个一分钟的视频，机器人在家里完成了浇花、叠衣服的工作后，陪小孩玩耍”

- **零额外费用模式（默认）**：Antigravity 会自动打开 Google Flow，用你 Google AI Ultra 账号自带的月度 10,000 积分（首次在浏览器点一下登录即可），站内锁死主角外貌 → 批量生成 8 秒真动态 Veo 3.1 视频 → 自动配音、压制字幕并导出 `final.mp4`。
- **纯 API 并发模式（可选）**：如希望走 Google Gemini API（Veo 3.1）或火山引擎即梦 Seedance API，在项目根目录新建 `.env` 填入 `GEMINI_API_KEY` 或 `VOLCENGINE_API_KEY` 即可自动切换。
