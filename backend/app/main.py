"""Lamarin: server FastAPI (API + frontend statis)."""

import base64
import binascii
import json
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import analyzer, config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Lamarin", docs_url="/api/docs", redoc_url=None)

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


@app.middleware("http")
async def _no_stale_assets(request: Request, call_next):
    """Peramban wajib memvalidasi ulang file frontend, supaya versi baru langsung terpakai setelah deploy."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    # Di belakang proxy hosting (Vercel/Render) alamat pengguna ada di X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "lokal")
    now = time.monotonic()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= config.RATE_PER_MINUTE:
        raise HTTPException(429, "Terlalu banyak pemeriksaan dalam satu menit. Tunggu sebentar.")
    q.append(now)


class CheckRequest(BaseModel):
    teks: str | None = Field(default=None, max_length=config.MAX_TEXT_CHARS)
    gambar: str | None = Field(default=None, description="base64 tanpa prefiks data:")
    mime: str | None = None


@app.exception_handler(ValueError)
async def _value_error(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/api/status")
def status():
    return {"ai_tersedia": config.ai_available(),
            "model": config.GEMINI_MODEL if config.ai_available() else None}


@app.post("/api/periksa")
def check(body: CheckRequest, request: Request):
    _rate_limit(request)
    teks = (body.teks or "").strip()
    image = None
    if body.gambar:
        if body.mime not in ALLOWED_MIME:
            raise HTTPException(400, "Format gambar harus PNG, JPG, atau WEBP.")
        try:
            image = base64.b64decode(body.gambar, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(400, "Data gambar rusak. Coba unggah ulang.")
        if len(image) > config.MAX_IMAGE_BYTES:
            raise HTTPException(413, "Gambar terlalu besar. Maksimal 4 MB.")
        if not config.ai_available() and not teks:
            raise HTTPException(400, "Pembaca gambar AI belum aktif. Gunakan pembaca teks di peramban atau tempel teksnya.")
    if not teks and not image:
        raise HTTPException(400, "Tempel teks lowongan atau unggah gambarnya dulu.")
    if teks and len(teks) < 15:
        raise HTTPException(400, "Teks terlalu pendek untuk diperiksa. Tempel isi lowongan selengkapnya.")
    return analyzer.analyze(teks or None, image, body.mime)


@app.get("/api/contoh")
def examples():
    """Contoh nyata dari set uji, untuk dicoba pengguna. Selalu dengan sumbernya."""
    out = []
    for fname, label in (("contoh_penipuan.json", "penipuan"), ("contoh_asli.json", "asli")):
        path = config.DATA_DIR / fname
        if not path.exists():
            continue
        items = {i["id"]: i for i in json.loads(path.read_text(encoding="utf-8"))}
        for item_id in SHOWCASE[label]:
            item = items.get(item_id)
            if item:
                out.append({"label": label, "teks": item["teks_lowongan"], "sumber": item["url"],
                            "judul": item.get("judul_artikel") or item.get("perusahaan", "")})
    return out


# Contoh yang ditampilkan di halaman: beragam modus, termasuk kasus yang terkait Bali.
SHOWCASE = {
    "penipuan": ["scam-27", "scam-22", "scam-13", "scam-16"],
    "asli": ["asli-02", "asli-14", "asli-23"],
}


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
