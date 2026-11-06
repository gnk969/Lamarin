"""Titik masuk Vercel (fungsi Python). Seluruh permintaan diteruskan ke aplikasi FastAPI di backend/app."""

import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app as _lamarin  # noqa: E402

_PREFIX = "/api/index"


class _RestorePath:
    """Bila hosting meneruskan permintaan dengan path fungsi (/api/index...), kembalikan ke path aslinya."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path == _PREFIX or path.startswith(_PREFIX + "/"):
                new = path[len(_PREFIX):] or "/"
                scope = dict(scope, path=new, raw_path=new.encode())
        await self.inner(scope, receive, send)


_lamarin.add_middleware(_RestorePath)
app: FastAPI = _lamarin
