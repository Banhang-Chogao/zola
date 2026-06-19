"""
Optional, opt-in TLS/SSL support for the FastAPI backend services.

Why this exists
---------------
In production these services run behind a TLS-terminating proxy (Render,
Cloudflare, nginx, …). The platform start command is::

    uvicorn main:app --host 0.0.0.0 --port $PORT

so the Python process serves plain HTTP and the edge handles HTTPS. That path
is intentionally left untouched — this module never runs there.

This helper adds *application-level* TLS for self-hosted / bare-metal
deployments where Python itself must terminate TLS (e.g. ``python main.py`` on
your own VM). It is the single place where ``import ssl`` lives.

Safety rules (mirrors the request that introduced this module)
--------------------------------------------------------------
* Development mode never forces SSL — default is plain HTTP.
* Production enables SSL only when BOTH the cert and key files exist.
* Missing / unreadable cert config => return ``None`` => caller serves plain
  HTTP. We never crash a server just because TLS could not be configured.
* Never auto-generate certificates. Never assume a deployment platform or a
  hardcoded cert path — everything is driven by environment variables.

Configuration (environment variables)
-------------------------------------
* ``SSL_CERTFILE`` (aliases: ``TLS_CERTFILE``, ``SSL_CERT_FILE``) — PEM cert chain.
* ``SSL_KEYFILE``  (aliases: ``TLS_KEYFILE``, ``SSL_KEY_FILE``)  — PEM private key.
* ``SSL_ENABLED`` / ``FORCE_SSL`` — ``1/true/on`` to opt in, ``0/false/off`` to
  opt out. When unset, SSL turns on automatically only in production *and* only
  when the cert files are present.
* ``ENV`` / ``ENVIRONMENT`` / ``APP_ENV`` / ``PYTHON_ENV`` — ``production`` (or
  ``prod`` / ``live``) marks production; anything else is treated as dev.
* ``HOST`` (default ``0.0.0.0``) and ``PORT`` (default ``8000``) for ``run()``.

Public API
----------
* ``build_ssl_context(...)`` — returns a configured ``ssl.SSLContext`` (usable
  by any server: uvicorn programmatic, hypercorn, raw ``asyncio``/socket) or
  ``None`` when TLS should stay off.
* ``ssl_enabled()`` / ``cert_paths()`` / ``is_production()`` — decision helpers.
* ``uvicorn_ssl_kwargs()`` — ``ssl_certfile`` / ``ssl_keyfile`` kwargs for
  ``uvicorn.run(...)`` (empty dict when TLS is off).
* ``run(app)`` — convenience self-hosted launcher used by each service's
  ``if __name__ == "__main__":`` block.
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from typing import Optional

__all__ = [
    "is_production",
    "cert_paths",
    "build_ssl_context",
    "ssl_enabled",
    "uvicorn_ssl_kwargs",
    "run",
]

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}
_PROD_NAMES = {"prod", "production", "live"}


def _env(*names: str, default: str = "") -> str:
    """Return the first non-empty value among ``names`` (env var aliases)."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val.strip()
    return default


def is_production() -> bool:
    """True when the environment marks this as a production deployment."""
    env = _env("ENV", "ENVIRONMENT", "APP_ENV", "PYTHON_ENV", default="development")
    return env.lower() in _PROD_NAMES


def cert_paths() -> tuple[Optional[str], Optional[str]]:
    """Return ``(certfile, keyfile)`` from the environment, or ``(None, None)``."""
    certfile = _env("SSL_CERTFILE", "TLS_CERTFILE", "SSL_CERT_FILE")
    keyfile = _env("SSL_KEYFILE", "TLS_KEYFILE", "SSL_KEY_FILE")
    return (certfile or None, keyfile or None)


def _files_present(certfile: Optional[str], keyfile: Optional[str]) -> bool:
    """True only when both paths are set and point at readable files."""
    try:
        return bool(
            certfile
            and keyfile
            and Path(certfile).is_file()
            and Path(keyfile).is_file()
        )
    except OSError:
        # Never let a filesystem probe crash the caller — treat as "no certs".
        return False


def build_ssl_context(
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    *,
    require: bool = False,
) -> Optional[ssl.SSLContext]:
    """Build a TLS *server* context, or return ``None`` to serve plain HTTP.

    This is the canonical SSL wiring point:

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=..., keyfile=...)

    Parameters
    ----------
    certfile, keyfile:
        Override the env-derived paths. When both are ``None`` the values from
        :func:`cert_paths` are used.
    require:
        When ``True`` and the cert/key files are missing, raise
        ``FileNotFoundError`` instead of silently returning ``None``. Use this
        only when the caller has explicitly opted into TLS and wants a hard
        failure on misconfiguration.
    """
    if certfile is None and keyfile is None:
        certfile, keyfile = cert_paths()

    if not _files_present(certfile, keyfile):
        if require:
            raise FileNotFoundError(
                "TLS requested but certificate/key files were not found "
                f"(certfile={certfile!r}, keyfile={keyfile!r}). Set SSL_CERTFILE "
                "and SSL_KEYFILE to existing PEM files."
            )
        return None

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    # Conservative, modern hardening — no behaviour change for callers, just
    # refuses obsolete protocol versions. SSLv2/3 and compression are already
    # disabled by PROTOCOL_TLS_SERVER defaults.
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def ssl_enabled() -> bool:
    """Decide whether SSL should be activated for this process.

    * ``SSL_ENABLED``/``FORCE_SSL`` falsy  -> never (explicit opt-out).
    * ``SSL_ENABLED``/``FORCE_SSL`` truthy -> yes, but only if cert files exist
      (we still refuse to "force" TLS with no certificate).
    * unset -> production + certs present. Dev defaults to plain HTTP.
    """
    flag = _env("SSL_ENABLED", "FORCE_SSL").lower()
    if flag in _FALSY:
        return False

    present = _files_present(*cert_paths())
    if flag in _TRUTHY:
        return present
    return is_production() and present


def uvicorn_ssl_kwargs() -> dict:
    """SSL kwargs for ``uvicorn.run(**kwargs)`` — empty when TLS is off."""
    if not ssl_enabled():
        return {}
    certfile, keyfile = cert_paths()
    if not _files_present(certfile, keyfile):
        return {}
    return {"ssl_certfile": certfile, "ssl_keyfile": keyfile}


def run(app, *, host: Optional[str] = None, port: Optional[int] = None, **extra) -> None:
    """Run an ASGI app under uvicorn, enabling TLS only when it is safe to.

    Intended for a service's ``if __name__ == "__main__":`` block on a
    self-hosted box. The platform start command (``uvicorn main:app``) does not
    use this, so production-on-Render behaviour is unchanged.

    ``app`` may be an import string (``"main:app"``) or the application object.
    Prefer the import string so uvicorn's reload/worker handling works.
    """
    import uvicorn  # local import: only needed on the self-hosted run path

    host = host or _env("HOST", default="0.0.0.0")
    port = int(port or _env("PORT", default="8000"))

    if ssl_enabled():
        certfile, keyfile = cert_paths()
        # Validate the cert/key up front via the ssl module (fail fast with a
        # clear error) before handing the paths to uvicorn, which builds its
        # own context for the listening socket.
        build_ssl_context(certfile, keyfile, require=True)
        ssl_kwargs = {"ssl_certfile": certfile, "ssl_keyfile": keyfile}
        scheme = "https"
    else:
        ssl_kwargs = {}
        scheme = "http"

    print(
        f"[ssl_support] starting uvicorn on {scheme}://{host}:{port} "
        f"(tls={'on' if ssl_kwargs else 'off'}, production={is_production()})"
    )
    uvicorn.run(app, host=host, port=port, **ssl_kwargs, **extra)
