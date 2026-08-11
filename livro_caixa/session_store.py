from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob_from_bytes(value: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(value)
    blob = _DataBlob(
        len(value),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


def _protect(value: str) -> bytes:
    raw = value.encode("utf-8")
    source, source_buffer = _blob_from_bytes(raw)
    destination = _DataBlob()
    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source),
        "Livro Caixa",
        None,
        None,
        None,
        0,
        ctypes.byref(destination),
    )
    del source_buffer
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


def _unprotect(value: bytes) -> str:
    source, source_buffer = _blob_from_bytes(value)
    destination = _DataBlob()
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(destination),
    )
    del source_buffer
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


class SessionStore:
    """Guarda somente o token de renovação, protegido pelo Windows DPAPI."""

    def __init__(self, path: Path | None = None) -> None:
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        self.path = path or local_app_data / "LivroCaixa" / "session.dat"

    def load(self) -> str | None:
        if os.name != "nt" or not self.path.exists():
            return None
        try:
            protected = base64.b64decode(self.path.read_bytes(), validate=True)
            return _unprotect(protected)
        except (OSError, ValueError, UnicodeError):
            self.clear()
            return None

    def save(self, refresh_token: str) -> None:
        if os.name != "nt" or not refresh_token:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(base64.b64encode(_protect(refresh_token)))
        temporary.replace(self.path)

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
