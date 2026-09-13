"""CPU-only recognizer. JSON messages on private pipes; no transcript logging."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import wave

RATE = 16000
WINDOW = 512
MAX_SECONDS = 120


def words_only(text: str) -> str:
    return ''.join(c for c in text if not c.isspace() and not unicodedata.category(c).startswith('P'))


def join_chunks(parts: list[str]) -> str:
    result = ''
    for part in parts:
        part = part.strip()
        if result and part and result[-1].isascii() and result[-1].isalnum() and part[0].isascii() and part[0].isalnum():
            result += ' '
        result += part
    return result


class Recognizer:
    def __init__(self, models: Path):
        # These imports belong only in the isolated speech environment.
        import numpy as np
        import sherpa_onnx as sherpa
        from opencc import OpenCC

        self.np, self.sherpa = np, sherpa
        self.asr = sherpa.OfflineRecognizer.from_sense_voice(
            model=str(models / 'sensevoice.int8.onnx'), tokens=str(models / 'tokens.txt'),
            num_threads=4, provider='cpu', language='yue', use_itn=False,
        )
        config = sherpa.VadModelConfig()
        config.silero_vad.model = str(models / 'silero_vad.onnx')
        config.silero_vad.threshold = 0.5
        config.silero_vad.min_silence_duration = 0.6
        config.silero_vad.min_speech_duration = 0.2
        config.silero_vad.max_speech_duration = 20
        config.silero_vad.window_size = WINDOW
        config.sample_rate, config.num_threads, config.provider = RATE, 1, 'cpu'
        self.vad = sherpa.VoiceActivityDetector(config, buffer_size_in_seconds=30)
        punc_config = sherpa.OfflinePunctuationConfig()
        punc_config.model.ct_transformer = str(models / 'punctuation.int8.onnx')
        punc_config.model.num_threads, punc_config.model.provider = 1, 'cpu'
        self.punctuation = sherpa.OfflinePunctuation(punc_config)
        self.traditional = OpenCC('s2hk')

    def take_segments(self) -> list[str]:
        parts = []
        while not self.vad.empty():
            samples = self.vad.front.samples.copy()
            self.vad.pop()
            stream = self.asr.create_stream()
            stream.accept_waveform(RATE, samples)
            self.asr.decode_stream(stream)
            text = re.sub(r'<\|[^|]*\|>', '', stream.result.text).strip()
            if text:
                parts.append(text)
        return parts

    def finish(self, parts: list[str], punctuation: bool) -> str:
        text = join_chunks(parts)
        if text and punctuation:
            punctuated = self.punctuation.add_punctuation(text)
            # A punctuation pass is not authorized to rewrite vocabulary.
            if words_only(punctuated) == words_only(text):
                text = punctuated
        return self.traditional.convert(text).strip()

    def transcribe_pcm(self, pcm: bytes, punctuation: bool = True) -> str:
        self.vad.reset()
        parts = []
        samples = self.np.frombuffer(pcm, dtype='<i2').astype('float32') / 32768
        for start in range(0, len(samples), WINDOW):
            chunk = samples[start:start + WINDOW]
            if len(chunk) < WINDOW:
                chunk = self.np.pad(chunk, (0, WINDOW - len(chunk)))
            self.vad.accept_waveform(chunk)
            parts.extend(self.take_segments())
        self.vad.flush()
        parts.extend(self.take_segments())
        return self.finish(parts, punctuation)


class Recording:
    def __init__(self, recognizer: Recognizer, request: dict, emit):
        self.recognizer, self.request, self.emit = recognizer, request, emit
        self.cancelled = threading.Event()
        self.stopped = threading.Event()
        self.frames = queue.Queue(maxsize=4096)  # bounded to ~131 seconds
        command = ['pw-record', '--raw', '--rate', str(RATE), '--channels', '1',
                   '--format', 's16', '--media-role', 'Communication',
                   '--sample-count', str(RATE * MAX_SECONDS)]
        if request.get('microphone', 'default') != 'default':
            command += ['--target', request['microphone']]
        self.process = subprocess.Popen(command + ['-'], stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL)
        self.thread = threading.Thread(target=self.decode, daemon=True)
        self.reader = threading.Thread(target=self.capture, daemon=True)
        self.thread.start()
        self.reader.start()

    def message(self, kind: str, **values):
        if not self.cancelled.is_set():
            self.emit({'event': kind, 'id': self.request['id'], **values})

    def stop(self, cancel: bool = False):
        if cancel:
            self.cancelled.set()
        if not self.stopped.is_set():
            self.stopped.set()
            if self.process.poll() is None:
                self.process.terminate()

    def capture(self):
        total, last_level = 0, 0.0
        try:
            while not self.cancelled.is_set():
                pcm = self.process.stdout.read(WINDOW * 2)
                if not pcm:
                    break
                total += len(pcm) // 2
                self.frames.put(pcm, timeout=1)
                now = time.monotonic()
                if now - last_level >= 0.1:
                    samples = self.recognizer.np.frombuffer(pcm, dtype='<i2').astype('float32')
                    rms = float(self.recognizer.np.sqrt(self.recognizer.np.mean(samples ** 2))) / 32768
                    self.message('level', level=min(1, rms * 6), elapsed=total / RATE)
                    last_level = now
            if not self.stopped.is_set() and total < RATE * (MAX_SECONDS - 1):
                self.message('error', message='Microphone stopped. Check the selected input device.')
                self.cancelled.set()
            elif not self.cancelled.is_set():
                self.message('finishing')
        except (OSError, queue.Full):
            self.message('error', message='Could not capture microphone audio.')
            self.cancelled.set()
        finally:
            self.stop()
            self.process.stdout.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            try:
                self.frames.put_nowait(None)
            except queue.Full:
                self.cancelled.set()
                while not self.frames.empty():
                    try:
                        self.frames.get_nowait()
                    except queue.Empty:
                        break
                self.frames.put_nowait(None)

    def decode(self):
        parts = []
        asr = self.recognizer
        asr.vad.reset()
        try:
            while True:
                pcm = self.frames.get()
                if pcm is None:
                    break
                if self.cancelled.is_set():
                    continue
                samples = asr.np.frombuffer(pcm, dtype='<i2').astype('float32') / 32768
                if len(samples) < WINDOW:
                    samples = asr.np.pad(samples, (0, WINDOW - len(samples)))
                asr.vad.accept_waveform(samples)
                parts.extend(asr.take_segments())
            if not self.cancelled.is_set():
                asr.vad.flush()
                parts.extend(asr.take_segments())
                text = asr.finish(parts, self.request.get('punctuation', True))
                self.message('result', text=text)
        except Exception:
            self.message('error', message='Speech recognition failed. Try starting dictation again.')
            self.stop(cancel=True)
        finally:
            asr.vad.reset()
            parts.clear()


class WindowsRecording(Recording):
    """PortAudio capture; shares the tested VAD/decode path with PipeWire."""

    def __init__(self, recognizer: Recognizer, request: dict, emit):
        import sounddevice as sd

        self.recognizer, self.request, self.emit = recognizer, request, emit
        self.cancelled = threading.Event()
        self.stopped = threading.Event()
        self.stream_lock = threading.Lock()
        self.frames = queue.Queue(maxsize=4096)
        device = request.get('microphone', 'default')
        from .windows_devices import input_parameters
        self.stream = sd.RawInputStream(
            samplerate=RATE, channels=1, dtype='int16', blocksize=WINDOW,
            **input_parameters(device, sd),
        )
        try:
            self.stream.start()
        except Exception:
            self.stream.close()
            raise
        self.thread = threading.Thread(target=self.decode, daemon=True)
        self.reader = threading.Thread(target=self.capture, daemon=True)
        self.thread.start()
        self.reader.start()

    def capture_error(self):
        self.message('error', message='Could not capture microphone audio. Check Windows microphone access.')
        self.cancelled.set()

    def stop(self, cancel: bool = False):
        if cancel:
            self.cancelled.set()
        with self.stream_lock:
            if not self.stopped.is_set():
                self.stopped.set()
                try:
                    self.stream.abort()
                except Exception:
                    # A disconnected device can fail during shutdown as well
                    # as read. Do not break the UI or strand the decoder.
                    self.capture_error()

    def capture(self):
        total, last_level = 0, 0.0
        try:
            while not self.stopped.is_set() and total < RATE * MAX_SECONDS:
                data, overflowed = self.stream.read(WINDOW)
                if overflowed:
                    raise RuntimeError('Microphone overflow')
                pcm = bytes(data)
                self.frames.put(pcm, timeout=1)
                total += len(pcm) // 2
                now = time.monotonic()
                if now - last_level >= 0.1:
                    samples = self.recognizer.np.frombuffer(pcm, dtype='<i2').astype('float32')
                    rms = float(self.recognizer.np.sqrt(self.recognizer.np.mean(samples ** 2))) / 32768
                    self.message('level', level=min(1, rms * 6), elapsed=total / RATE)
                    last_level = now
        except Exception:
            if not self.stopped.is_set():
                self.capture_error()
        finally:
            self.stop()
            try:
                with self.stream_lock:
                    self.stream.close()
            except Exception:
                self.capture_error()
            if not self.cancelled.is_set():
                self.message('finishing')
            # Keep draining possible even after cancellation/recognizer errors.
            while True:
                try:
                    self.frames.put(None, timeout=0.1)
                    break
                except queue.Full:
                    self.cancelled.set()
                    try:
                        self.frames.get_nowait()
                    except queue.Empty:
                        pass


def serve(models: Path):
    def terminate(_signum, _frame):
        # Run the cleanup below so disabling dictation also closes pw-record.
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, terminate)
    output_lock = threading.Lock()

    def emit(message):
        with output_lock:
            print(json.dumps(message, ensure_ascii=False), flush=True)

    recognizer = Recognizer(models)
    emit({'event': 'ready', 'provider': 'cpu', 'model': 'SenseVoice Small Yue INT8'})
    job = None
    try:
        for line in sys.stdin:
            request = json.loads(line)
            action = request.get('action')
            if action == 'start':
                if job and (job.thread.is_alive() or job.reader.is_alive()):
                    emit({'event': 'error', 'id': request['id'], 'message': 'Previous dictation is still stopping. Try again.'})
                    continue
                try:
                    capture = WindowsRecording if sys.platform == 'win32' else Recording
                    job = capture(recognizer, request, emit)
                    emit({'event': 'recording', 'id': request['id']})
                except Exception:
                    emit({'event': 'error', 'id': request['id'], 'message': 'Could not start microphone recording.'})
            elif job and request.get('id') == job.request['id'] and action in ('stop', 'cancel'):
                job.stop(cancel=action == 'cancel')
    finally:
        if job:
            job.stop(cancel=True)
            job.thread.join(timeout=5)


def main():
    # Explicit CPU providers above; also prevent accidental CUDA visibility.
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--wav', type=Path, help='Transcribe a supplied 16 kHz mono PCM WAV instead of listening')
    parser.add_argument('--check', action='store_true', help='Initialize CPU models and check silence without a microphone')
    args = parser.parse_args()
    if args.check:
        assert Recognizer(args.models).transcribe_pcm(bytes(RATE * 2)) == ''
        print(json.dumps({'ready': True, 'provider': 'cpu'}))
    elif args.wav:
        with wave.open(str(args.wav)) as source:
            if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (RATE, 1, 2):
                parser.error('Expected 16 kHz mono 16-bit PCM WAV')
            pcm = source.readframes(RATE * MAX_SECONDS + 1)
            if len(pcm) > RATE * MAX_SECONDS * 2:
                parser.error('Maximum file duration is 120 seconds')
        before = time.monotonic()
        recognizer = Recognizer(args.models)
        loaded = time.monotonic()
        print(json.dumps({'text': recognizer.transcribe_pcm(pcm), 'provider': 'cpu',
                          'load_seconds': loaded - before,
                          'recognition_seconds': time.monotonic() - loaded}, ensure_ascii=False))
    else:
        serve(args.models)


if __name__ == '__main__':
    main()
