# Local HTTPS test fixtures

These certificates and the intentionally public server key are used only by
`tests/test_downloads.py` on a loopback HTTPS server. They are not production
credentials and must never be installed in a system certificate store.
The root private key was discarded. The certificates expire on 2040-01-01;
regenerate the fixtures before that date. Tests load the CA only into their
individual client contexts. The server certificate covers `localhost`, not
`127.0.0.1`, so hostname rejection can be tested independently of CA trust.
