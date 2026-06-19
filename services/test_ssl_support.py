"""
Unit tests for services/ssl_support.py.

Run from the repo root::

    python3 services/test_ssl_support.py
    python3 -m unittest discover -s services -p 'test_ssl_support.py'

These tests cover the decision logic (dev vs prod, certs present vs missing,
explicit opt-in / opt-out) and the SSL context construction. They never touch
the network and never start a server.
"""

import os
import ssl
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ssl_support  # noqa: E402

# Every env var that influences ssl_support — cleared before each test so the
# host environment can't leak into assertions.
_ENV_KEYS = (
    "SSL_CERTFILE", "TLS_CERTFILE", "SSL_CERT_FILE",
    "SSL_KEYFILE", "TLS_KEYFILE", "SSL_KEY_FILE",
    "SSL_ENABLED", "FORCE_SSL",
    "ENV", "ENVIRONMENT", "APP_ENV", "PYTHON_ENV",
    "HOST", "PORT",
)


def _make_self_signed(dirpath: str):
    """Create a throwaway self-signed cert/key pair, or return None if we cannot.

    Tests are skipped (not failed) when no certificate toolkit is available, so
    the suite stays green in minimal environments. We never ship generated
    certs — this is test-only scaffolding.
    """
    certfile = os.path.join(dirpath, "cert.pem")
    keyfile = os.path.join(dirpath, "key.pem")

    # Prefer the openssl CLI: it is light and avoids importing the optional
    # `cryptography` wheel (which can panic at import time on some boxes).
    import shutil
    import subprocess

    if shutil.which("openssl"):
        try:
            subprocess.run(
                [
                    "openssl", "req", "-x509", "-newkey", "rsa:2048",
                    "-keyout", keyfile, "-out", certfile, "-days", "1",
                    "-nodes", "-subj", "/CN=localhost",
                ],
                check=True,
                capture_output=True,
            )
            return certfile, keyfile
        except Exception:
            pass

    # Fallback: the `cryptography` package, if it imports cleanly.
    try:
        import datetime

        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = datetime.datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256())
        )
        with open(certfile, "wb") as fh:
            fh.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(keyfile, "wb") as fh:
            fh.write(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                )
            )
        return certfile, keyfile
    except BaseException:
        # BaseException, not just Exception: a broken `cryptography` wheel can
        # raise pyo3_runtime.PanicException. Skip the test rather than fail.
        return None


class SSLSupportTest(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in _ENV_KEYS}
        for k in _ENV_KEYS:
            os.environ.pop(k, None)
        self._tmp = tempfile.TemporaryDirectory()
        # Two touch-files that merely *exist* (enough for the path checks; not
        # valid PEM, used to assert decisions that don't build a real context).
        self.cert = os.path.join(self._tmp.name, "cert.pem")
        self.key = os.path.join(self._tmp.name, "key.pem")
        Path(self.cert).write_text("x")
        Path(self.key).write_text("x")

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    # ---- is_production ----------------------------------------------------
    def test_default_is_development(self):
        self.assertFalse(ssl_support.is_production())

    def test_production_aliases(self):
        for val in ("production", "prod", "Live", "PRODUCTION"):
            os.environ["ENV"] = val
            self.assertTrue(ssl_support.is_production(), val)
            os.environ.pop("ENV")

    def test_non_prod_env_is_dev(self):
        os.environ["ENVIRONMENT"] = "staging"
        self.assertFalse(ssl_support.is_production())

    # ---- cert_paths -------------------------------------------------------
    def test_cert_paths_empty(self):
        self.assertEqual(ssl_support.cert_paths(), (None, None))

    def test_cert_paths_aliases(self):
        os.environ["TLS_CERTFILE"] = self.cert
        os.environ["SSL_KEY_FILE"] = self.key
        self.assertEqual(ssl_support.cert_paths(), (self.cert, self.key))

    # ---- ssl_enabled matrix ----------------------------------------------
    def test_dev_no_certs_disabled(self):
        self.assertFalse(ssl_support.ssl_enabled())

    def test_dev_with_certs_no_flag_disabled(self):
        os.environ["SSL_CERTFILE"] = self.cert
        os.environ["SSL_KEYFILE"] = self.key
        # Dev must not force SSL even when certs happen to be present.
        self.assertFalse(ssl_support.ssl_enabled())

    def test_dev_with_certs_and_flag_enabled(self):
        os.environ["SSL_CERTFILE"] = self.cert
        os.environ["SSL_KEYFILE"] = self.key
        os.environ["SSL_ENABLED"] = "true"
        self.assertTrue(ssl_support.ssl_enabled())

    def test_flag_true_but_no_certs_disabled(self):
        os.environ["FORCE_SSL"] = "1"
        # Never "force" TLS without a certificate — safe fallback.
        self.assertFalse(ssl_support.ssl_enabled())

    def test_prod_no_certs_disabled(self):
        os.environ["ENV"] = "production"
        self.assertFalse(ssl_support.ssl_enabled())

    def test_prod_with_certs_enabled(self):
        os.environ["ENV"] = "production"
        os.environ["SSL_CERTFILE"] = self.cert
        os.environ["SSL_KEYFILE"] = self.key
        self.assertTrue(ssl_support.ssl_enabled())

    def test_prod_with_certs_but_explicit_off(self):
        os.environ["ENV"] = "production"
        os.environ["SSL_CERTFILE"] = self.cert
        os.environ["SSL_KEYFILE"] = self.key
        os.environ["SSL_ENABLED"] = "off"
        self.assertFalse(ssl_support.ssl_enabled())

    # ---- uvicorn_ssl_kwargs ----------------------------------------------
    def test_uvicorn_kwargs_empty_when_disabled(self):
        self.assertEqual(ssl_support.uvicorn_ssl_kwargs(), {})

    def test_uvicorn_kwargs_when_enabled(self):
        os.environ["ENV"] = "production"
        os.environ["SSL_CERTFILE"] = self.cert
        os.environ["SSL_KEYFILE"] = self.key
        self.assertEqual(
            ssl_support.uvicorn_ssl_kwargs(),
            {"ssl_certfile": self.cert, "ssl_keyfile": self.key},
        )

    # ---- build_ssl_context ------------------------------------------------
    def test_build_context_none_when_missing(self):
        self.assertIsNone(ssl_support.build_ssl_context("/no/cert", "/no/key"))

    def test_build_context_require_raises(self):
        with self.assertRaises(FileNotFoundError):
            ssl_support.build_ssl_context("/no/cert", "/no/key", require=True)

    def test_build_context_success(self):
        pair = _make_self_signed(self._tmp.name)
        if not pair:
            self.skipTest("no certificate toolkit (cryptography/openssl) available")
        certfile, keyfile = pair
        ctx = ssl_support.build_ssl_context(certfile, keyfile)
        self.assertIsInstance(ctx, ssl.SSLContext)
        self.assertEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
