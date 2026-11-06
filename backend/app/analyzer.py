"""Menggabungkan pemeriksaan aturan dan AI menjadi skor risiko yang bisa diaudit.

- Aturan selalu jalan (gratis, tanpa jaringan).
- AI (Gemini) membaca gambar, mengekstrak fakta, dan menemukan rambu kontekstual.
- Rambu dari AI hanya diterima bila kutipan buktinya benar-benar ada di teks lowongan.
- Skor = jumlah bobot rambu unik (maks 100). Bobot ditetapkan di rambu.py, bukan oleh AI.
"""

import difflib
import logging
import re

from . import config, gemini, rules
from .rambu import KATALOG, level_for

log = logging.getLogger("rambu.analyzer")

LANGKAH_UMUM = [
    "Cek lowongan yang sama di situs karier atau akun media sosial resmi perusahaan.",
    "Jangan mentransfer uang atau mengirim KTP, rekening, OTP, atau PIN sebelum kamu yakin.",
    "Laporkan lowongan mencurigakan ke Kemnaker (hotline 1500 630) atau kanal aduan resmi lainnya.",
]
LANGKAH_KHUSUS = {
    "LUAR_NEGERI_TANPA_IZIN": "Untuk kerja luar negeri, pastikan perusahaannya berizin P3MI. Tanyakan ke BP3MI Bali atau Disnaker setempat.",
    "TAUTAN_MENCURIGAKAN": "Jangan mengisi formulir dari tautan itu. Buka situs resmi perusahaan dengan mengetik alamatnya sendiri.",
    "MINTA_BIAYA": "Tolak permintaan biaya apa pun. Rekrutmen resmi tidak memungut biaya dari pelamar.",
    "TRAVEL_WAJIB": "Jangan membeli tiket lewat agen yang ditunjuk perekrut. Ini modus yang sering dipakai.",
    "DEPOSIT_TUGAS": "Jangan mengisi deposit. Uang deposit pada modus ini hampir tidak pernah kembali.",
    "CATUT_PERUSAHAAN": "Hubungi perusahaan lewat kontak di situs resminya untuk memastikan lowongan ini.",
}


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w@./:+-]+", " ", s.lower()).split())


def evidence_in_text(bukti: str, text: str) -> bool:
    """True bila kutipan AI ada di teks (persis atau sangat mirip)."""
    b, t = _norm(bukti), _norm(text)
    if not b or len(b) < 4:
        return False
    if b in t:
        return True
    window = len(b)
    best = 0.0
    step = max(1, window // 4)
    for i in range(0, max(1, len(t) - window + 1), step):
        best = max(best, difflib.SequenceMatcher(None, b, t[i:i + window]).ratio())
        if best >= 0.85:
            return True
    return False


def analyze(text: str | None, image: bytes | None = None, mime: str | None = None,
            use_ai: bool = True) -> dict:
    text = (text or "").strip()
    warnings: list[str] = []
    ai_data: dict | None = None
    mode = "aturan"

    if use_ai and config.ai_available():
        try:
            ai_data = gemini.analyze(text or None, image, mime)
            mode = "aturan+ai"
        except gemini.AIUnavailable as exc:
            warnings.append(f"Pemeriksaan AI tidak tersedia: {exc} Hasil di bawah memakai aturan saja.")
        except Exception as exc:  # jangan gagalkan permintaan karena galat tak terduga
            log.exception("AI gagal")
            warnings.append(f"Pemeriksaan AI gagal ({type(exc).__name__}). Hasil di bawah memakai aturan saja.")

    if image and not text:
        text = str((ai_data or {}).get("teks_terbaca", "")).strip()
        if not text:
            raise ValueError("Teks pada gambar belum bisa dibaca. Coba tempel teks lowongannya.")

    found: dict[str, dict] = {}
    for t in rules.detect(text):
        found[t.kode] = {"kode": t.kode, "bukti": t.bukti, "sumber": ["aturan"], "alasan_ai": ""}

    rejected = 0
    for item in (ai_data or {}).get("rambu", []) or []:
        kode = str(item.get("kode", ""))
        bukti = str(item.get("bukti", "")).strip()[:200]
        if kode not in KATALOG:
            continue
        if not evidence_in_text(bukti, text):
            rejected += 1
            continue
        alasan = str(item.get("alasan", "")).strip()[:300]
        if kode in found:
            if "ai" not in found[kode]["sumber"]:
                found[kode]["sumber"].append("ai")
            found[kode]["alasan_ai"] = alasan
        else:
            found[kode] = {"kode": kode, "bukti": bukti, "sumber": ["ai"], "alasan_ai": alasan}
    if rejected:
        warnings.append(f"{rejected} temuan AI diabaikan karena kutipannya tidak ada di teks lowongan.")

    rambu = []
    for kode, f in found.items():
        r = KATALOG[kode]
        rambu.append({**f, "judul": r.judul, "bobot": r.bobot, "penjelasan": r.alasan})
    rambu.sort(key=lambda x: -x["bobot"])

    score = min(100, sum(r["bobot"] for r in rambu))
    level, label = level_for(score)
    steps = [LANGKAH_KHUSUS[r["kode"]] for r in rambu if r["kode"] in LANGKAH_KHUSUS] + LANGKAH_UMUM

    fakta = (ai_data or {}).get("fakta") or {}
    if not fakta:
        fakta = {
            "kontak": [m.group() for m in rules.PHONE_RE.finditer(text.lower())][:5],
            "tautan": rules.domains_in(text)[:5],
        }

    return {
        "mode": mode,
        "skor": score,
        "level": level,
        "label": label,
        "rambu": rambu,
        "fakta": fakta,
        "ringkasan_ai": str((ai_data or {}).get("ringkasan", "")).strip()[:400],
        "teks_diperiksa": text[: config.MAX_TEXT_CHARS],
        "langkah": steps[:6],
        "peringatan": warnings,
    }
