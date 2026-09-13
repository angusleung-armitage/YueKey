"""Real TLS checks for the model downloader; no external network or CA-store writes."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from quick_hk import speech_assets as assets

FIXTURES = Path(__file__).parent / 'fixtures/tls'
BODY = b'YueKey verified model fixture'
CHECKSUM = hashlib.sha256(BODY).hexdigest()


@contextmanager
def https_server(*, failures=0, retry_after='0'):
    pending = [failures]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            if self.path == '/limited' and pending[0] > 0:
                pending[0] -= 1
                self.send_response(429)
                self.send_header('Retry-After', retry_after)
                self.end_headers()
                return
            if self.path == '/redirect':
                self.send_response(302)
                self.send_header('Location', '/model')
                self.end_headers()
                return
            offset = int(self.headers.get('Range', 'bytes=0-').split('=')[1].split('-')[0])
            self.send_response(206 if offset else 200)
            self.send_header('Content-Length', str(len(BODY) - offset))
            if offset:
                self.send_header('Content-Range', f'bytes {offset}-{len(BODY) - 1}/{len(BODY)}')
            self.end_headers()
            self.wfile.write(BODY[offset:])

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(FIXTURES / 'server.pem', FIXTURES / 'server.key')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class DownloadTlsTests(unittest.TestCase):
    def setUp(self):
        import os
        proxy = patch.dict(os.environ, {'no_proxy': 'localhost,127.0.0.1'})
        proxy.start()
        self.addCleanup(proxy.stop)

    def context(self, *, trusted):
        context = assets.https_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        if sys.platform == 'win32':
            import truststore
            self.assertIsInstance(context, truststore.SSLContext)
        if trusted:
            context.load_verify_locations(cafile=str(FIXTURES / 'ca.pem'))
        return context

    def test_verified_https_redirect_and_partial_resume(self):
        context = self.context(trusted=True)
        with https_server() as port, tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.onnx'
            partial = path.with_name('model.onnx.part')
            partial.write_bytes(BODY[:7])
            with patch.object(assets, 'https_context', return_value=context):
                assets.download(f'https://localhost:{port}/redirect', path, CHECKSUM)
            self.assertEqual(path.read_bytes(), BODY)
            self.assertFalse(partial.exists())

    def test_untrusted_issuer_and_wrong_hostname_preserve_files(self):
        for trusted, hostname in ((False, 'localhost'), (True, '127.0.0.1')):
            with self.subTest(trusted=trusted, hostname=hostname):
                context = self.context(trusted=trusted)
                with https_server() as port, tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / 'model.onnx'
                    partial = path.with_name('model.onnx.part')
                    path.write_bytes(b'existing model')
                    partial.write_bytes(b'partial model')
                    with patch.object(assets, 'https_context', return_value=context):
                        with self.assertRaises(assets.DownloadCertificateError) as raised:
                            assets.download(f'https://{hostname}:{port}/model', path, CHECKSUM)
                    self.assertIn('model.onnx', str(raised.exception))
                    self.assertIn(hostname, str(raised.exception))
                    self.assertIsNotNone(raised.exception.__cause__)
                    self.assertEqual(path.read_bytes(), b'existing model')
                    self.assertEqual(partial.read_bytes(), b'partial model')

    def test_rate_limit_retry_resumes_verified_partial_download(self):
        context = self.context(trusted=True)
        with https_server(failures=2) as port, tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.onnx'
            path.with_name('model.onnx.part').write_bytes(BODY[:7])
            with patch.object(assets, 'https_context', return_value=context):
                assets.download(f'https://localhost:{port}/limited', path, CHECKSUM)
            self.assertEqual(path.read_bytes(), BODY)

    def test_rate_limit_is_bounded_and_respects_long_cooldowns(self):
        context = self.context(trusted=True)
        for retry_after, waits in (('0', 3), ('120', 0)):
            with self.subTest(retry_after=retry_after), \
                    https_server(failures=10, retry_after=retry_after) as port, \
                    tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'model.onnx'
                path.write_bytes(b'existing model')
                with patch.object(assets, 'https_context', return_value=context), \
                        patch.object(assets.time, 'sleep') as sleep:
                    with self.assertRaises(assets.urllib.error.HTTPError):
                        assets.download(f'https://localhost:{port}/limited', path, CHECKSUM)
                self.assertEqual(sleep.call_count, waits)
                self.assertEqual(path.read_bytes(), b'existing model')


if __name__ == '__main__':
    unittest.main()
