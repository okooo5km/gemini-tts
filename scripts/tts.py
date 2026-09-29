#!/usr/bin/env python3
"""Gemini 3.8 TTS REST client. Author: okooo5km(十里)."""
import argparse
import base64
import getpass
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request
import wave
import warnings

MODEL = 'gemini-3.8-flash-tts'
ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions'


def config_path():
    return Path(os.environ.get('GEMINI_TTS_CONFIG', '~/.config/gemini-tts/config.json')).expanduser()


def read_config():
    path = config_path()
    if not path.exists():
        return {}
    if os.name == 'posix' and path.stat().st_mode & 0o077:
        raise ValueError(f'Config must be private: chmod 600 {path}')
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Config must be a JSON object')
    return value


def configure():
    if not sys.stdin.isatty():
        raise ValueError('Run configure in an interactive terminal; alternatively set GEMINI_API_KEY')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            key = getpass.getpass('Gemini API key (hidden): ').strip()
        except getpass.GetPassWarning:
            raise ValueError('Hidden input unavailable; use a native terminal or an environment variable') from None
    if not key:
        raise ValueError('Empty key; configuration unchanged')
    path = config_path()
    config = read_config()
    config['api_key'] = key
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.config-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(config, output)
            output.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f'Saved private config: {path}')


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


CONTROL_FIELDS = {
    'emotion': '情绪', 'pace': '语速', 'accent': '口音',
    'delivery': '表达方式', 'emphasis': '重音要求',
    'prosody': '韵律变化', 'lengthening': '词语延长', 'pauses': '停顿方式',
}


def combined_style(args):
    parts = [args.style] if args.style else []
    for field, label in CONTROL_FIELDS.items():
        value = getattr(args, field, None)
        if value:
            parts.append(f'{label}：{value}')
    return '；'.join(parts)


def payload(args):
    style_default = combined_style(args)
    if args.dialogue:
        dialog = json.loads(Path(args.dialogue).expanduser().read_text(encoding='utf-8-sig'))
        speakers = dialog.get('speakers', [])
        if not isinstance(speakers, list) or len(speakers) != 2:
            raise ValueError('Dialogue requires exactly two speakers')
        names = set()
        normalized = []
        for speaker in speakers:
            name = nonempty(speaker.get('speaker'), 'speaker')
            voice = nonempty(speaker.get('voice'), 'voice')
            if voice.startswith(('voice_', 'voicekey_')):
                raise ValueError('Dialogue requires prebuilt voices')
            names.add(name)
            normalized.append({'speaker': name, 'voice': voice})
        if len(names) != 2:
            raise ValueError('Speaker names must be unique')
        turns = dialog.get('turns', [])
        if not isinstance(turns, list) or not turns:
            raise ValueError('Dialogue requires turns')
        content = []
        for turn in turns:
            if turn.get('speaker') not in names:
                raise ValueError('Every turn must reference a configured speaker')
            style = turn.get('style', style_default)
            if not isinstance(style, str):
                raise ValueError('style must be a string')
            content.append({'type': 'text', 'text': nonempty(turn.get('text'), 'text'),
                            'annotations': [{'type': 'speech_metadata', 'speaker': turn['speaker'], 'style': style}]})
        speech = {'mode': 'conversational', 'speakers': normalized}
    else:
        text = args.text if args.text is not None else (sys.stdin.read().removeprefix('\ufeff') if args.file == '-' else Path(args.file).expanduser().read_text(encoding='utf-8-sig'))
        content = [{'type': 'text', 'text': nonempty(text, 'text'),
                    'annotations': [{'type': 'speech_metadata', 'style': style_default}]}]
        speech = [{'voice': nonempty(args.voice, 'voice')}]
    return {'model': MODEL, 'input': [{'type': 'user_input', 'content': content}],
            'response_format': {'type': 'audio', 'mime_type': 'audio/wav'},
            'generation_config': {'speech_config': speech}}


def decode_audio(result):
    blocks = [part for step in result.get('steps', []) if step.get('type') == 'model_output'
              for part in step.get('content', []) if part.get('type') == 'audio']
    if not blocks:
        raise ValueError('API returned no audio; no file written')
    audio = base64.b64decode(blocks[-1]['data'], validate=True)
    with wave.open(io.BytesIO(audio), 'rb') as wav:
        if wav.getnframes() == 0:
            raise ValueError('API returned empty WAV')
        frames = wav.readframes(wav.getnframes())
        if len(frames) != wav.getnframes() * wav.getnchannels() * wav.getsampwidth():
            raise ValueError('API returned truncated WAV; no file written')
        info = {'duration_seconds': round(wav.getnframes() / wav.getframerate(), 3),
                'sample_rate': wav.getframerate(), 'channels': wav.getnchannels()}
    return audio, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('controls', help='Show speech controls and inline tag examples (offline)')
    sub.add_parser('configure', help='Save API key through a hidden terminal prompt')
    generate = sub.add_parser('generate', help='Generate a WAV file')
    source = generate.add_mutually_exclusive_group(required=True)
    source.add_argument('--text')
    source.add_argument('--file', help='UTF-8 transcript; - reads stdin')
    source.add_argument('--dialogue', help='JSON with speakers and turns')
    generate.add_argument('--voice', default='Kore', help='Voice name, e.g. Kore or Puck; default: Kore')
    generate.add_argument('--style', default='', help='Free-form acting instructions; combined with the controls below')
    for field, example in {
        'emotion': '温暖、鼓励，带一点笑意',
        'pace': '像朋友聊天，前半句稍快，后半句放慢',
        'accent': '自然普通话',
        'delivery': '像对一个人说话，避免播音腔',
        'emphasis': '强调“不是只有”，结尾笃定',
        'prosody': '轻重和语调随情绪与语义自然变化，不要每句套同一种起伏',
        'lengthening': '在犹豫或感慨处适当延长个别词，不固定拖长每句尾音',
        'pauses': '停顿跟随思考和语义，长短自然，不按每个逗号等长停顿',
    }.items():
        generate.add_argument('--' + field, help=f'Natural-language direction, e.g. {example}')
    generate.add_argument('--out', required=True)
    generate.add_argument('--dry-run', action='store_true', help='Print request without credentials or network access')
    generate.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    if args.command == 'controls':
        print((Path(__file__).resolve().parent.parent / 'references' / 'speech-controls.md').read_text(encoding='utf-8'))
        return
    if args.command == 'configure':
        configure()
        return
    body = payload(args)
    if args.dry_run:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return
    destination = Path(args.out).expanduser().resolve()
    if destination.suffix.lower() != '.wav':
        raise ValueError('--out must use the .wav extension')
    if destination.exists():
        raise ValueError('Output already exists; choose a new filename')
    if not destination.parent.is_dir():
        raise ValueError('Output parent directory does not exist')
    if args.timeout <= 0:
        raise ValueError('--timeout must be positive')
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or read_config().get('api_key')
    if not key or not isinstance(key, str) or not key.strip():
        raise ValueError('Set GEMINI_API_KEY or run: tts.py configure')
    request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json', 'x-goog-api-key': key.strip()})
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        # Do not echo provider bodies, which can contain input text or credentials.
        raise ValueError(f'Gemini HTTP {error.code}; check credentials, model access, quota, or request. No automatic retry.') from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError('Network error or timeout; generation may have been billed. No automatic retry.') from None
    audio, info = decode_audio(result)
    with destination.open('xb') as output:
        output.write(audio)
    print(json.dumps({'path': str(destination), 'model': MODEL, 'bytes': len(audio), **info}, ensure_ascii=False))


def configure_stdio():
    # Redirected Windows streams may otherwise use a legacy code page.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')


if __name__ == '__main__':
    configure_stdio()
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, AttributeError, wave.Error, EOFError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
