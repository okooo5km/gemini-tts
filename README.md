# Gemini TTS

A reusable AI-agent skill and dependency-free Python CLI for expressive speech with **Gemini 3.8 Flash TTS**. Works with Codex, Claude Code, and other agents that load `SKILL.md`.

将文本生成 WAV 语音，支持单人旁白、双人对话，以及情绪、语速、重音、停顿和词语延长等自然语言控制。[中文控制指南](references/speech-controls.md)。

## Requirements

- Python 3.10 or newer; no pip packages required.
- A Gemini API key with access to `gemini-3.8-flash-tts` and sufficient billing/quota.
- Internet access to Google's Gemini API. Speech generation can incur charges.

## Install as a shared skill

On macOS or Linux, keep one copy and link it to your agents:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/okooo5km/gemini-tts.git ~/.agents/skills/gemini-tts
mkdir -p ~/.codex/skills ~/.claude/skills
ln -s ~/.agents/skills/gemini-tts ~/.codex/skills/gemini-tts
ln -s ~/.agents/skills/gemini-tts ~/.claude/skills/gemini-tts
```

If a destination already exists, inspect it first; do not overwrite an existing installation. Other agents can load the same folder using their own skill discovery mechanism. Start a new agent session if needed to discover the skill. Agent-facing instructions and control examples are in Chinese; the CLI can accept transcripts and style instructions in other languages.

For standalone CLI use, clone anywhere and run `python3 scripts/tts.py` from the repository. On Windows, use `python` if appropriate; the shared symlink commands above are for macOS/Linux. Automated tests cover macOS and Linux.

## Configure credentials

Use an existing `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable, or run this in your own interactive terminal:

```bash
python3 ~/.agents/skills/gemini-tts/scripts/tts.py configure
```

The prompt hides input. Configuration is stored outside the skill at `~/.config/gemini-tts/config.json`; set `GEMINI_TTS_CONFIG` to choose another location. Precedence: `GEMINI_API_KEY` → `GOOGLE_API_KEY` → configuration `api_key`.

The file stores the key in **plaintext**, with mode `600` on POSIX systems. On Windows, protect the file with your account's filesystem permissions. Never put credentials in a prompt, script, command argument, example, or commit. Do not paste keys into issues.

## Generate speech

From the repository directory:

```bash
python3 scripts/tts.py generate \
  --text '不是只有伟大的艺术家，才能创造出好的作品。' \
  --voice Iapetus \
  --delivery '给朋友发一条语音，自然普通话，随口分享想法' \
  --out narration.wav
```

Use `--file transcript.txt` for a UTF-8 transcript or `--file -` for stdin. The output directory must exist. Existing files are never overwritten. Successful generation prints JSON with the absolute path, duration, sample rate, channels, and byte count.

### Expression controls

| Option | Controls |
| --- | --- |
| `--voice` | Voice identity; default `Kore`. Existing custom `voice_...` IDs work for single-speaker synthesis. |
| `--style` | Free-form direction |
| `--emotion` | Emotion |
| `--pace` | Speaking pace |
| `--accent` | Language/accent |
| `--delivery` | Delivery and volume |
| `--emphasis` | Words to emphasize |
| `--prosody` | Intonation and rhythmic variation |
| `--lengthening` | Contextual word elongation |
| `--pauses` | Meaning-driven pauses |

All expression options are composed into `speech_metadata.style`; they are **prompt guidance**, not precise pitch, timing, or randomization controls. Start with a concrete conversational situation and a few relevant directions. Natural variation should follow meaning and emotion. Dialect accuracy is not guaranteed. Input text is preserved; inline tags such as `<short pause>` or `<sigh>` are passed through unchanged.

```bash
python3 scripts/tts.py controls
python3 scripts/tts.py generate --help
python3 scripts/tts.py generate --text '你好。' --out sample.wav --dry-run
```

`--dry-run` prints the request, including the transcript, without reading credentials or accessing the network.

### Two-speaker dialogue

```bash
python3 scripts/tts.py generate --dialogue examples/dialogue.json --out dialogue.wav
```

Configure exactly two distinct speakers using prebuilt voices. Each turn names a speaker and includes text. A turn's `style` replaces the inherited CLI directions for that turn; omitting it inherits them. Voice creation, voice cloning, streaming, and automatic long-text chunking are not implemented.

## Privacy and errors

Generation sends the transcript and style instructions to Google. The client sends credentials in an HTTP header to a fixed HTTPS endpoint; it does not log keys or raw API responses. Generated audio stays at your selected output path.

Requests are not automatically retried or switched to another model. A timeout can occur after billable generation has started. HTTP 402 usually requires reviewing project billing; 401/403 indicate authentication or access issues; 429 indicates quota/rate limits. Check [Google's billing guide](https://ai.google.dev/gemini-api/docs/billing) and your project status before retrying.

Responses must contain valid, nonempty, untruncated WAV audio. The returned WAV already has a header; no extra header is added. A metadata lookup alone does not prove generation quota is available.

## Development

```bash
python3 -m unittest discover -s tests -v
```

Tests use temporary files and mocked HTTP responses: no API key, network access, or paid generation required. CI runs the same suite. Prior manual smoke tests confirmed single-speaker WAV generation; they do not establish audio quality for every voice or language.

```text
SKILL.md                     Agent instructions
agents/openai.yaml           Codex UI metadata
scripts/tts.py               Python CLI
references/speech-controls.md Control guidance
examples/dialogue.json       Two-speaker input example
tests/test_tts.py             Offline behavior tests
.github/workflows/tests.yml  CI
LICENSE                      MIT license
```

API documentation: [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation). This is an independent project, not an official Google product. The MIT license covers this project's code and documentation; use of Google's API remains subject to Google's terms.
