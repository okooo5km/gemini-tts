# Gemini TTS

A reusable AI-agent skill and dependency-free Python CLI for expressive speech with **Gemini 3.8 Flash TTS**. Works with Codex, Claude Code, and other agents that load `SKILL.md`.

将文本生成 WAV 语音，支持单人旁白、双人对话、指定已有自定义音色，以及情绪、语速、重音、停顿和词语延长等自然语言控制。[中文控制指南](references/speech-controls.md)。

## Requirements

- Python 3.10 or newer; no pip packages required.
- Node.js 22.20 or newer for the optional Agent Skills CLI install; speech generation itself needs no Node.js.
- A Gemini API key with access to `gemini-3.8-flash-tts` and sufficient billing/quota.
- Internet access to Google's Gemini API. Speech generation can incur charges.

## Install

### Agent Skills CLI (recommended)

Install the skill into Codex, Claude Code, Cursor, and other supported agents with the open [Agent Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add okooo5km/gemini-tts
```

The installer detects the repository's root `SKILL.md` and lets you choose the target agents and scope. To make the skill available across all projects, install globally:

```bash
npx skills add okooo5km/gemini-tts -g
```

To skip the prompts and target specific agents:

```bash
npx skills add okooo5km/gemini-tts -g -a codex claude-code -y
```

Only these install commands need Node.js (22.20 or newer); generating speech needs Python only. Update or uninstall later:

```bash
npx skills update gemini-tts -g
npx skills remove gemini-tts -g
```

A global install lives in `~/.agents/skills/gemini-tts`, and supported agents discover that copy (or a link to it) automatically. Start a new agent session if the skill does not appear. Agent-facing instructions and control examples are in Chinese; the CLI can accept transcripts and style instructions in other languages.

### Manual install for development

Use this only when you want to pin a revision or edit the skill itself. On macOS or Linux, keep one copy and link it to your agents:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/okooo5km/gemini-tts.git ~/.agents/skills/gemini-tts
mkdir -p ~/.codex/skills ~/.claude/skills
ln -s ~/.agents/skills/gemini-tts ~/.codex/skills/gemini-tts
ln -s ~/.agents/skills/gemini-tts ~/.claude/skills/gemini-tts
```

If a destination already exists, inspect it first; do not overwrite an existing installation. Updates come from `git pull`, not `npx skills update`. For standalone CLI use without any agent, clone anywhere and run `python3 scripts/tts.py` from the repository. Automated tests cover macOS, Linux, and Windows.

### Windows PowerShell

`npx skills add` works the same way in PowerShell:

```powershell
npx skills add okooo5km/gemini-tts -g -a codex
py -3 -X utf8 "$HOME/.agents/skills/gemini-tts/scripts/tts.py" configure
```

Use Python 3.10+ (`py -3 --version`, or verify `python --version`). For a manual installation that you update with `git pull`, clone into a user-owned folder and use directory junctions:

```powershell
$skillDir = Join-Path $HOME '.agents/skills/gemini-tts'
New-Item -ItemType Directory -Force (Split-Path $skillDir) | Out-Null
git clone https://github.com/okooo5km/gemini-tts.git "$skillDir"
New-Item -ItemType Directory -Force "$HOME/.codex/skills", "$HOME/.claude/skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME/.codex/skills/gemini-tts" -Target "$skillDir"
New-Item -ItemType Junction -Path "$HOME/.claude/skills/gemini-tts" -Target "$skillDir"
py -3 -X utf8 "$skillDir/scripts/tts.py" configure
py -3 -X utf8 "$skillDir/scripts/tts.py" generate --text '你好。' --out './hello.wav'
```

Do not overwrite existing directories. If junctions are unavailable, copy the skill into the agent's skill directory and keep copies updated. Use `python -X utf8` when the `py` launcher is unavailable. PowerShell does not use Bash line continuations or `export`. Full examples for UTF-8 files, paths with spaces, environment variables, and Python integration are in the [platform guide](references/platforms.md).

## Use with an agent

After installation, describe the task or call the skill explicitly:

```text
Use $gemini-tts to read this transcript in warm, natural Mandarin and save it to ~/Downloads/narration.wav.
```

The agent locates `scripts/tts.py` in the installed skill, runs it, and returns the audio path. Installed skills with Chinese instructions also work from other languages; transcripts and style directions can be Chinese, English, or any language the model supports.

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

Use `--file transcript.txt` for a UTF-8 transcript (with or without BOM) or `--file -` for UTF-8 stdin. JSON input accepts UTF-8 BOM too. On Windows PowerShell 5.1, use `Set-Content -Encoding UTF8` instead of default redirection to create files; prefer file input over legacy shell pipelines. CLI output is UTF-8, including when redirected. The output directory must exist. Existing files are never overwritten. Successful generation prints JSON with the absolute path, duration, sample rate, channels, and byte count.

### Expression controls

| Option | Controls |
| --- | --- |
| `--voice` | Voice identity; default `Kore`. Prebuilt names, `voice_...` IDs, `voicekey_...` keys, and saved aliases all work. |
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

Configure exactly two distinct speakers using prebuilt voices. Each turn names a speaker and includes text. A turn's `style` replaces the inherited CLI directions for that turn; omitting it inherits them. A replicated voice cannot be passed to the two-speaker mode: Gemini only accepts prebuilt voices inside a single multi-speaker request, so synthesize each custom-voice turn separately and concatenate the audio. Streaming and automatic long-text chunking are not implemented.

## Use an existing custom voice

Pass a voice ID obtained from [Google AI Studio](https://aistudio.google.com/generate-speech) directly to `--voice`:

```bash
python3 scripts/tts.py generate \
  --text 'This is my own voice.' --voice voice_YOUR_VOICE_ID \
  --out narration.wav
```

The skill generates speech only: it does not record, create, list, rename, or delete voices and does not run a local studio or server. A custom voice's display name is not its API ID. Use an API key with access to the voice's project; invalid or inaccessible voices fail rather than silently falling back to a prebuilt voice.

Prebuilt voice names, existing `voice_...` IDs, and valid `voicekey_...` values remain supported. Existing local aliases are still resolved for backward compatibility; this skill does not add or manage aliases or change existing configuration. Treat `voicekey_...` as a secret: do not publish it in prompts, logs, or source control. A dry run displays the supplied voice value, so use placeholders in shared examples.

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
SKILL.md                       Agent instructions
agents/openai.yaml             Codex UI metadata
scripts/tts.py                 Python CLI for speech generation
references/speech-controls.md  Control guidance
references/platforms.md        Platform-specific execution guidance
examples/dialogue.json         Two-speaker input example
tests/                         Offline behavior tests
.github/workflows/tests.yml    CI
LICENSE                        MIT license
```

API documentation: [Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation) and [Voice replication](https://ai.google.dev/gemini-api/docs/voice-replication). Use only custom voices you are authorized to use, subject to Google's [prohibited use policy](https://policies.google.com/terms/generative-ai/use-policy). This is an independent project, not an official Google product. The MIT license covers this project's code and documentation; use of Google's API remains subject to Google's terms.
