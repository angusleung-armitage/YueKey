"""Portable, checksum-verified speech model downloads. SPDX-License-Identifier: MIT."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import os
from pathlib import Path
import shutil
import ssl
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

ASR_BASE = ('https://huggingface.co/csukuangfj/'
            'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/'
            'resolve/355f4d4884d8afd08aef04b9007a8556d7b463b2/')
ASSETS = {
    'sensevoice.int8.onnx': (ASR_BASE + 'model.int8.onnx', '12ca1a2ae7ecf3e0019ef2822307ee0b5cadc9196569e379b4c4026f8205276d'),
    'tokens.txt': (ASR_BASE + 'tokens.txt', 'f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc'),
    'silero_vad.onnx': ('https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx', '9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6'),
    'punctuation.tar.bz2': ('https://github.com/k2-fsa/sherpa-onnx/releases/download/punctuation-models/sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8.tar.bz2', 'c0d5aa5f8eeb686032345e180bedf39319dc2e0556781c6264bcadba8328a6e1'),
}
PUNCT_HASH = '65a3fb9f5ad7bfb96bf69e0dc4481df97f6ee60513c1d94ce981ba6effd524b1'


def digest(path: Path) -> str:
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def model_hashes() -> dict[str, str]:
    return {**{k: v[1] for k, v in ASSETS.items() if not k.endswith('.bz2')},
            'punctuation.int8.onnx': PUNCT_HASH}


def https_context():
    """Use native Windows chain building, including intermediate CA retrieval."""
    if sys.platform == 'win32':
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context()


class DownloadCertificateError(RuntimeError):
    """A download could not be authenticated; existing files are retained."""


def download(url: str, destination: Path, expected: str) -> None:
    for attempt in range(4):
        try:
            _download_once(url, destination, expected)
            return
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            delay = 10 * 2 ** attempt
            retry_after = error.headers.get('Retry-After')
            if retry_after:
                try:
                    delay = max(0, int(retry_after))
                except ValueError:
                    try:
                        delay = max(0, (parsedate_to_datetime(retry_after)
                                        - datetime.now(timezone.utc)).total_seconds())
                    except (TypeError, ValueError, OverflowError):
                        pass
            if delay > 60:
                raise  # A long server cooldown needs a later user retry.
            error.close()
            time.sleep(delay)


def _download_once(url: str, destination: Path, expected: str) -> None:
    if destination.is_file() and digest(destination) == expected:
        return
    partial = destination.with_name(destination.name + '.part')
    if partial.is_file() and digest(partial) == expected:
        os.replace(partial, destination)
        return
    offset = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
    try:
        with urllib.request.urlopen(request, timeout=60, context=https_context()) as source:
            append = offset > 0 and source.status == 206
            if append and not source.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise RuntimeError('Model server returned an invalid download range')
            with partial.open('ab' if append else 'wb') as output:
                shutil.copyfileobj(source, output)
    except (urllib.error.URLError, ssl.SSLCertVerificationError) as error:
        reason = getattr(error, 'reason', error)
        if not isinstance(reason, ssl.SSLCertVerificationError):
            raise
        host = urllib.parse.urlsplit(url).hostname
        detail = getattr(reason, 'verify_message', None) or str(reason)
        raise DownloadCertificateError(
            f'未能驗證下載伺服器憑證 · Certificate verification failed\n'
            f'{destination.name} · {host}\n{detail}\n'
            '請檢查系統日期／時間及系統信任的憑證，再重試。\n'
            'Check the system date/time and trusted certificates, then retry. '
            'On a managed network, ask IT to check its HTTPS inspection certificate.'
        ) from error
    if digest(partial) != expected:
        partial.unlink()
        raise RuntimeError(f'Checksum mismatch for {destination.name}; model was not installed')
    os.replace(partial, destination)



def prepare_models(models: Path, progress=lambda message: None) -> None:
    models.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in ASSETS.items():
        progress(f"Preparing {name}…")
        download(url, models / name, expected)
    target = models / "punctuation.int8.onnx"
    if not target.is_file() or digest(target) != PUNCT_HASH:
        partial = target.with_suffix(".part")
        with tarfile.open(models / "punctuation.tar.bz2") as archive:
            member = next(m for m in archive if m.name.endswith("/model.int8.onnx") and m.isfile())
            with archive.extractfile(member) as source, partial.open("wb") as output:
                shutil.copyfileobj(source, output)
        if digest(partial) != PUNCT_HASH:
            partial.unlink()
            raise RuntimeError("Punctuation model checksum mismatch")
        partial.replace(target)
