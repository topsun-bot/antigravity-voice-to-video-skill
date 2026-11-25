# 分镜脚本模板与 `script.json` v2.0 电影级规范

每个项目目录 `projects/<slug>/` 同时维护：
- `script.md`：给老板快速审阅的分镜表。
- `script.json`：驱动 `prepare_subjects.py`、`generate_tts.py`、`generate_videos.py`、`build_video.py` 的唯一数据源（Single Source of Truth）。

---

## `script.json` v2.0 完整结构

```json
{
  "project_name": "cinema-2028-demo",
  "title": "未来呼啸而来 · 2028",
  "aspect_ratio": "16:9",
  "fps": 24,
  "theme": "dark",
  "production": {
    "mode": "cinematic_ai",
    "video_provider": "auto",
    "veo_tier": "fast",
    "resolution": "720p",
    "max_concurrency": 4,
    "generate_audio": false
  },
  "style_bible": "Photorealistic 35mm cinema film look, warm morning sunlight, soft architectural shadows, natural color grading, shallow depth of field, clean modern minimalist future aesthetic, ultra detailed, 24fps filmic motion.",
  "subjects": [
    {
      "id": "protagonist",
      "name": "主角（科技创始人）",
      "role": "character",
      "description": "38-year-old Chinese male tech executive, neat short black hair, dark charcoal cashmere sweater and tailored trousers, calm confident smile",
      "reference_image": "assets/subjects/protagonist.png"
    },
    {
      "id": "robot_zero",
      "name": "白色管家机器人 Zero",
      "role": "character",
      "description": "Sleek matte-white humanoid home assistant robot, smooth minimalist oval head, articulated white limbs with dark carbon joints, subtle cyan glow ring at chest",
      "reference_image": "assets/subjects/robot_zero.png"
    }
  ],
  "tts": {
    "voice": "zh-CN-YunxiNeural",
    "rate": "+2%",
    "pitch": "+0Hz"
  },
  "bgm": {
    "path": "",
    "volume": 0.14
  },
  "subtitles": {
    "enabled": true,
    "style": "cinema_pill",
    "font_name": "Noto Sans CJK SC",
    "font_size": 40,
    "margin_v": 46
  },
  "scenes": [
    {
      "id": "01",
      "label": "清晨启程",
      "chapter": "PART 01 · 清晨唤醒与智能出行",
      "narration": "系好安全带，搭乘时光机穿越到 2028 年的清晨。",
      "duration": 6.0,
      "audio_path": "",
      "visual": {
        "type": "ai_video",
        "tier": "quality",
        "subjects": ["protagonist", "robot_zero"],
        "first_frame": "assets/keyframes/scene_01.png",
        "image_prompt": "Wide cinematic morning shot in front of a modern sunlit villa...",
        "video_prompt": "Slow cinematic dolly-in shot, the Chinese executive steps smoothly into a sleek white autonomous gullwing pod while the white humanoid robot waves gently from the stone porch...",
        "camera": "slow dolly-in, 35mm lens, subtle natural handheld steadicam",
        "generated_video": "work/generated_videos/scene_01.mp4",
        "accent": "#38BDF8"
      }
    },
    {
      "id": "04",
      "label": "片尾收束",
      "chapter": "",
      "narration": "",
      "duration": 3.5,
      "audio_path": "",
      "visual": {
        "type": "outro_card",
        "title": "未来呼啸而来 · 2028",
        "subtitle": "科技从不线性爬行，而是指数级重塑世界"
      }
    }
  ]
}
```

## 支持的 `visual.type` 类型

| 类型 | 用途 | 关键字段 |
| :--- | :--- | :--- |
| `ai_video` | **电影级动态镜头（主力）** | `subjects`（最多 3 个）、`first_frame`、`image_prompt`、`video_prompt`、`camera`、`tier`（`lite`/`fast`/`quality`）、`generated_video` |
| `outro_card` | **极简深色电影片尾卡** | `title`、`subtitle`（自动淡入淡出） |
| `video` | 本地实拍/录屏素材 | `path`、`start`、`keep_audio` |
| `image` | 静态图片（支持 Ken Burns 运镜） | `path`、`zoom` |
| `card` | 科技感信息卡片（适合数据/干货） | `title`、`subtitle`、`bullets`、`accent` |

## 支持的字幕样式 (`subtitles.style`)

- `cinema_pill`（默认）：**圆角半透明深灰底 + 清晰白字**，抗锯齿渲染，复刻高端 AI 概念片风格。
- `ass`：传统描边字幕（适合超长视频 90 句以上自动回退）。
