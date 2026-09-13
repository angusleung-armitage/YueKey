#!/usr/bin/env python3
"""Freeze the CPU worker and fetch verified models for the all-in-one DEB."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from quick_hk.speech_assets import prepare_models, model_hashes, ASR_BASE, download
from runtime_licenses import collect_licenses


def build():
    models = ROOT / 'build/speech-models'
    prepare_models(models, lambda message: print(message, flush=True))
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--name', 'yuekey-speech', '--distpath', str(ROOT / 'build/linux-dist'),
        '--workpath', str(ROOT / 'build/linux-pyinstaller'), '--specpath', str(ROOT / 'build'),
        '--collect-all', 'sherpa_onnx', '--collect-all', 'opencc',
        '--exclude-module', 'readline',
        str(ROOT / 'src/quick_hk/dictation_worker.py'),
    ], check=True)
    bundle = ROOT / 'build/linux-dist/yuekey-speech'
    collect_licenses(bundle / 'LICENSES')
    command = [str(bundle / 'yuekey-speech'), '--models', str(models)]
    subprocess.run([*command, '--check'], check=True, timeout=120)
    sample = ROOT / 'build/public-yue-test.wav'
    download(ASR_BASE + 'test_wavs/yue-0.wav', sample,
             'd029018f0dcaf6bbd66f1f9c1633dc30846e809f4b698a14b70b0849cf77a266')
    result = json.loads(subprocess.check_output([*command, '--wav', str(sample)], timeout=120))
    assert result['provider'] == 'cpu' and '企鵝' in result['text'], result
    (bundle / 'models.json').write_text(json.dumps(model_hashes(), indent=2) + '\n')
    print('PASS frozen CPU runtime: silence and verified public Cantonese sample; no microphone')


if __name__ == '__main__':
    build()
