"""Offline regression tests. Author: okooo5km(十里)."""
import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import warnings
import unittest
from unittest.mock import patch
import urllib.error
import wave

SYSTEM_ENV = os.environ.copy()
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tts', ROOT / 'scripts/tts.py')
tts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts)


def wav_bytes():
    data = io.BytesIO()
    with wave.open(data, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b'\0\0' * 2400)
    return data.getvalue()


def response(audio):
    return {'steps': [{'type': 'model_output', 'content': [
        {'type': 'audio', 'data': base64.b64encode(audio).decode()}]}]}


class TTSTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'GEMINI_TTS_CONFIG': str(self.root / 'config.json')}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_cli(self, *args):
        with patch.object(tts.sys, 'argv', ['tts.py', *args]), contextlib.redirect_stdout(io.StringIO()) as out:
            tts.main()
        return out.getvalue()

    def test_dry_run_no_credentials_or_network(self):
        with patch.object(tts, 'read_config', side_effect=AssertionError), patch.object(tts.urllib.request, 'urlopen', side_effect=AssertionError):
            body = json.loads(self.run_cli('generate', '--text', '你好<short pause>世界', '--emotion', '开心', '--lengthening', '适当', '--out', 'unused.wav', '--dry-run'))
        part = body['input'][0]['content'][0]
        self.assertEqual(part['text'], '你好<short pause>世界')
        self.assertEqual(part['annotations'][0]['style'], '情绪：开心；词语延长：适当')

    def test_configure_private(self):
        with patch.object(tts.sys.stdin, 'isatty', return_value=True), patch.object(tts.getpass, 'getpass', return_value='fixture-secret'):
            result = self.run_cli('configure')
        self.assertNotIn('fixture-secret', result)
        self.assertEqual(tts.read_config()['api_key'], 'fixture-secret')
        if os.name == 'posix':
            self.assertEqual(tts.config_path().stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == 'posix', 'POSIX permissions')
    def test_reject_public_config(self):
        tts.config_path().write_text('{}')
        tts.config_path().chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private'):
            tts.read_config()

    def test_generate_and_env_precedence(self):
        audio = wav_bytes()
        def send(request, timeout):
            self.assertEqual(request.full_url, tts.ENDPOINT)
            self.assertEqual(request.get_header('X-goog-api-key'), 'env-fixture')
            self.assertEqual(json.loads(request.data)['model'], tts.MODEL)
            return io.BytesIO(json.dumps(response(audio)).encode())
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'env-fixture', 'GOOGLE_API_KEY': 'other-fixture'}), patch.object(tts, 'read_config', side_effect=AssertionError), patch.object(tts.urllib.request, 'urlopen', side_effect=send):
            result = json.loads(self.run_cli('generate', '--text', 'Hello', '--out', str(self.root / 'test.wav')))
        self.assertEqual(result['duration_seconds'], 0.1)
        self.assertEqual((self.root / 'test.wav').read_bytes(), audio)

    def test_existing_custom_voices_pass_through_without_config_or_network_in_dry_run(self):
        for voice in ('voice_fixture', 'voicekey_fixture'):
            with self.subTest(voice=voice), \
                    patch.object(tts, 'read_config', side_effect=AssertionError), \
                    patch.object(tts.urllib.request, 'urlopen', side_effect=AssertionError):
                body = json.loads(self.run_cli(
                    'generate', '--text', 'Hello', '--voice', voice,
                    '--out', 'unused.wav', '--dry-run'))
            self.assertEqual(body['generation_config']['speech_config'], [{'voice': voice}])

    def test_existing_custom_voice_generation_calls_only_the_synthesis_endpoint(self):
        audio = wav_bytes()
        for voice in ('voice_fixture', 'voicekey_fixture'):
            destination = self.root / f'{voice}.wav'

            def send(request, timeout):
                self.assertEqual(request.full_url, tts.ENDPOINT)
                self.assertEqual(request.get_method(), 'POST')
                speech = json.loads(request.data)['generation_config']['speech_config']
                self.assertEqual(speech, [{'voice': voice}])
                return io.BytesIO(json.dumps(response(audio)).encode())

            with self.subTest(voice=voice), \
                    patch.dict(os.environ, {'GEMINI_API_KEY': 'env-fixture'}), \
                    patch.object(tts, 'read_config', side_effect=AssertionError), \
                    patch.object(tts.urllib.request, 'urlopen', side_effect=send) as request:
                result = self.run_cli('generate', '--text', 'Hello', '--voice', voice,
                                      '--out', str(destination))
            self.assertEqual(request.call_count, 1)
            self.assertEqual(destination.read_bytes(), audio)
            self.assertEqual(json.loads(result)['sample_rate'], 24000)

    def test_existing_alias_remains_usable_without_modifying_configuration(self):
        config = tts.config_path()
        original = json.dumps({'api_key': 'fixture-secret',
                               'voices': {'旁白': 'voice_fixture'},
                               'last_voice': 'voice_old', 'extra': 'keep-me'}).encode()
        config.write_bytes(original)
        config.chmod(0o600)

        def send(request, timeout):
            self.assertEqual(json.loads(request.data)['generation_config']['speech_config'],
                             [{'voice': 'voice_fixture'}])
            return io.BytesIO(json.dumps(response(wav_bytes())).encode())

        with patch.object(tts.urllib.request, 'urlopen', side_effect=send):
            self.run_cli('generate', '--text', '你好', '--voice', '旁白',
                         '--out', str(self.root / 'alias.wav'))
        self.assertEqual(config.read_bytes(), original)

    def test_default_and_prebuilt_voice_names_remain_supported(self):
        default = json.loads(self.run_cli('generate', '--text', 'Hello',
                                          '--out', 'unused.wav', '--dry-run'))
        self.assertEqual(default['generation_config']['speech_config'], [{'voice': 'Kore'}])
        self.assertEqual(tts.resolve_voice('Puck'), 'Puck')

    def test_custom_voice_access_failure_never_falls_back_or_retries(self):
        error = urllib.error.HTTPError(tts.ENDPOINT, 403, 'Forbidden', {}, io.BytesIO(b'private'))
        destination = self.root / 'denied.wav'
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'env-fixture'}), \
                patch.object(tts.urllib.request, 'urlopen', side_effect=error) as request, \
                self.assertRaisesRegex(ValueError, 'HTTP 403'):
            self.run_cli('generate', '--text', 'Hello', '--voice', 'voice_fixture',
                         '--out', str(destination))
        self.assertEqual(request.call_count, 1)
        self.assertFalse(destination.exists())

    def test_dialogue_rejects_custom_voices_including_existing_aliases(self):
        config = tts.config_path()
        config.write_text(json.dumps({'voices': {'旁白': 'voice_fixture'}}))
        config.chmod(0o600)
        dialog = self.root / 'custom-dialogue.json'
        for voice in ('voice_fixture', 'voicekey_fixture', '旁白'):
            data = json.loads((ROOT / 'examples/dialogue.json').read_text())
            data['speakers'][0]['voice'] = voice
            dialog.write_text(json.dumps(data))
            with self.subTest(voice=voice), \
                    patch.object(tts.urllib.request, 'urlopen', side_effect=AssertionError), \
                    self.assertRaisesRegex(ValueError, 'prebuilt voices'):
                self.run_cli('generate', '--dialogue', str(dialog),
                             '--out', str(self.root / 'dialogue.wav'))

    def test_no_overwrite_or_request(self):
        out = self.root / 'test.wav'
        out.write_bytes(b'original')
        with patch.object(tts.urllib.request, 'urlopen', side_effect=AssertionError), self.assertRaisesRegex(ValueError, 'already exists'):
            self.run_cli('generate', '--text', 'Hello', '--out', str(out))
        self.assertEqual(out.read_bytes(), b'original')

    def test_dialogue_override_and_unknown_speaker(self):
        data = json.loads((ROOT / 'examples/dialogue.json').read_text())
        del data['turns'][1]['style']
        file = self.root / 'dialogue.json'
        def run():
            file.write_text(json.dumps(data))
            return json.loads(self.run_cli('generate', '--dialogue', str(file), '--style', 'inherited', '--out', 'unused.wav', '--dry-run'))
        parts = run()['input'][0]['content']
        self.assertEqual(parts[0]['annotations'][0]['style'], 'curious and relaxed')
        self.assertEqual(parts[1]['annotations'][0]['style'], 'inherited')
        data['turns'][0]['speaker'] = 'Unknown'
        with self.assertRaisesRegex(ValueError, 'configured speaker'):
            run()

    def test_invalid_audio(self):
        for value in ({}, response(b'not wav'), response(wav_bytes()[:-2])):
            with self.subTest(value=str(value)[:20]), self.assertRaises((ValueError, wave.Error, EOFError)):
                tts.decode_audio(value)

    def test_http_error_does_not_echo_or_retry(self):
        error = urllib.error.HTTPError(tts.ENDPOINT, 402, 'Payment required', {}, io.BytesIO(b'private transcript fixture-secret'))
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture-secret'}), patch.object(tts.urllib.request, 'urlopen', side_effect=error) as send:
            with self.assertRaises(ValueError) as caught:
                self.run_cli('generate', '--text', 'private transcript', '--out', str(self.root / 'error.wav'))
        self.assertIn('402', str(caught.exception))
        self.assertNotIn('fixture-secret', str(caught.exception))
        self.assertNotIn('private transcript', str(caught.exception))
        self.assertEqual(send.call_count, 1)
        self.assertFalse((self.root / 'error.wav').exists())

    def test_bom_transcript_and_dialogue(self):
        text = self.root / '中文 story.txt'
        text.write_text('你好，世界。', encoding='utf-8-sig')
        result = json.loads(self.run_cli('generate', '--file', str(text), '--out', 'unused.wav', '--dry-run'))
        self.assertEqual(result['input'][0]['content'][0]['text'], '你好，世界。')
        dialog = self.root / '对话.json'
        dialog.write_text((ROOT / 'examples/dialogue.json').read_text(encoding='utf-8'), encoding='utf-8-sig')
        result = json.loads(self.run_cli('generate', '--dialogue', str(dialog), '--out', 'unused.wav', '--dry-run'))
        self.assertEqual(len(result['input'][0]['content']), 2)

    def test_hidden_input_cannot_fall_back_to_echo(self):
        def unsafe_prompt(*args):
            warnings.warn('Cannot hide input', tts.getpass.GetPassWarning)
            raise AssertionError('Must stop before reading echoed input')
        with patch.object(tts.sys.stdin, 'isatty', return_value=True), patch.object(tts.getpass, 'getpass', side_effect=unsafe_prompt):
            with self.assertRaisesRegex(ValueError, 'Hidden input unavailable'):
                self.run_cli('configure')
        self.assertFalse(tts.config_path().exists())

    def test_configure_replaces_existing_file(self):
        with patch.object(tts.sys.stdin, 'isatty', return_value=True), patch.object(tts.getpass, 'getpass', side_effect=['first-fixture', 'second-fixture']):
            self.run_cli('configure')
            self.run_cli('configure')
        self.assertEqual(tts.read_config()['api_key'], 'second-fixture')
        self.assertEqual(list(self.root.glob('.config-*')), [])

    def test_real_cli_utf8_redirected_streams_and_foreign_cwd(self):
        env = SYSTEM_ENV.copy()
        env.update({'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0'})
        for key in ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_TTS_CONFIG']:
            env.pop(key, None)
        args = [sys.executable, str(ROOT / 'scripts/tts.py'), 'generate', '--file', '-', '--out', str(self.root / '中文 output.wav'), '--dry-run']
        run = subprocess.run(args, input='你好，世界。'.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.root, env=env, check=True)
        part = json.loads(run.stdout.decode('utf-8'))['input'][0]['content'][0]
        self.assertEqual(part['text'], '你好，世界。')
        run = subprocess.run([sys.executable, str(ROOT / 'scripts/tts.py'), 'controls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.root, env=env, check=True)
        self.assertIn('语音控制', run.stdout.decode('utf-8'))

    def test_controls_available(self):
        self.assertIn('--prosody', self.run_cli('controls'))


if __name__ == '__main__':
    unittest.main()
