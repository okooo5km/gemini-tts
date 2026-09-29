---
name: gemini-tts
description: 使用 Google Gemini 3.8 Flash TTS 将文本生成 WAV 语音，支持音色、语气、语速描述和双人对话。用于朗读、配音、旁白和播客语音生成，不用于语音识别或实时语音聊天。
---

# Gemini TTS

使用本技能目录内的 `scripts/tts.py`，仅依赖 Python 3 标准库。固定模型 `gemini-3.8-flash-tts`，通过 Google Interactions REST API 生成 WAV。

## 密钥

读取优先级：`GEMINI_API_KEY` → `GOOGLE_API_KEY` → 配置文件的 `api_key`。

让用户在自己的终端运行以下命令，输入过程隐藏：

```bash
python3 ~/.agents/skills/gemini-tts/scripts/tts.py configure
```

密钥保存在 `~/.config/gemini-tts/config.json`，权限为 `600`；用 `GEMINI_TTS_CONFIG` 指定其他配置路径。该文件是本地明文凭据，位于技能目录之外。已有环境变量可直接使用，无需写配置。不要把真实密钥写进脚本、技能、聊天、命令参数或版本库，不要读取或展示密钥内容。

## 表演控制

需要情绪、停顿或更自然的表达时，阅读 [语音控制速查](references/speech-controls.md)。调用者可通过 `--emotion`、`--pace`、`--accent`、`--delivery`、`--emphasis`、`--prosody`（韵律）、`--lengthening`（延长）、`--pauses`（停顿） 直接描述控制目标，或使用自由形式 `--style`；这些会合并成模型的风格指引。用 `tts.py controls` 查看带示例的完整说明，用 `tts.py generate --help` 查看参数。

普通话任务默认采用自然普通话；用户指定其他语言或口音时遵循其要求。自然表达应让情绪和语义带动重音、词长、语调和停顿，允许局部变化，不把“自然”处理成随机拖音或给每句套相同节奏。按需要选择少量控制项，不默认堆满参数，不改变标准读音，也不擅自添加语气词或改写原文。

局部停顿与发声标签直接写在正文里，不改动用户原文的词句。仅在用户要求表演增强时添加合适标签；不要把“自然”理解成必须叹气、咳嗽或笑出声。风格指引是生成提示，不保证精确时长或强度。

## 生成

保持用户提供的正文；除非用户要求，不改写。把情绪、口音和语速要求放进 `--style`，不要加进待朗读正文。默认音色 Kore；用户指定其他音色时使用其名称。长正文写入 UTF-8 文件，避免 shell 转义问题。

```bash
python3 ~/.agents/skills/gemini-tts/scripts/tts.py generate \
  --file /absolute/path/transcript.txt \
  --voice Kore --style '温暖自然的中文女声，语速适中' \
  --out /absolute/path/narration.wav
```

短文本可用 `--text '你好，世界。'`，管道输入可用 `--file -`。输出目录必须已存在；不会覆盖已有文件。`--dry-run` 仅检查并展示请求，不读取密钥、不调用网络，但会展示正文。网络超时默认 180 秒，可用 `--timeout` 调整。失败不自动重试或切换模型，避免重复计费；先判断错误再决定是否重试。

双人对话用 `--dialogue /absolute/path/dialogue.json`，结构如下：

```json
{
  "speakers": [
    {"speaker": "主持人", "voice": "Kore"},
    {"speaker": "嘉宾", "voice": "Puck"}
  ],
  "turns": [
    {"speaker": "主持人", "text": "今天聊什么？", "style": "好奇、轻快"},
    {"speaker": "嘉宾", "text": "聊聊文字如何变成声音。", "style": "自然、从容"}
  ]
}
```

此模式要求两个不同的角色名，每段必须匹配已配置角色，使用预置音色。此技能不创建或克隆声音。

调用成功后检查返回的时长、采样率和文件路径。脚本会验证 WAV 并直接保存，不能再包一层 WAV 文件头。向用户提供绝对路径音频嵌入 `![语音](/absolute/path/narration.wav)`。仅完成 dry-run 或离线测试时，不要声称已成功生成或试听。

## 官方参考

接口与提示方式核对日期：2026-09-28。需要更多音色或发声标签时查阅 [Google TTS 文档](https://ai.google.dev/gemini-api/docs/speech-generation)。持续语气用 `speech_metadata.style`；短暂停顿和非语言发声可用正文内标签，例如 `<short pause>`、`<sigh>`，仅在用户需求合适时添加。
