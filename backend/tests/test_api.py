"""Tes API tanpa memanggil Gemini sungguhan."""

import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RAMBU_AI"] = "off"
os.environ["RAMBU_CEK_TAUTAN"] = "off"

from fastapi.testclient import TestClient  # noqa: E402

from app import analyzer, config, gemini  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
SCAM = "Rekrutmen staf BUMN 2026. Daftar lewat bit.ly/daftar-bumn, kirim KTP via WA 081234567xxx. Biaya administrasi Rp250.000."


def test_status_and_frontend():
    assert client.get("/api/status").json()["ai_tersedia"] is False
    assert client.get("/").status_code == 200


def test_text_check_rules_only():
    r = client.post("/api/periksa", json={"teks": SCAM})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "aturan" and body["level"] == "tinggi"
    assert body["langkah"]


def test_validation_errors():
    assert client.post("/api/periksa", json={}).status_code == 400
    assert client.post("/api/periksa", json={"teks": "loker"}).status_code == 400
    png = base64.b64encode(b"\x89PNG fake").decode()
    assert client.post("/api/periksa", json={"gambar": png, "mime": "image/png"}).status_code == 400  # AI mati
    assert client.post("/api/periksa", json={"gambar": png, "mime": "image/gif"}).status_code == 400


def test_ai_merge_and_hallucination_guard(monkeypatch):
    fake = {
        "teks_terbaca": SCAM,
        "fakta": {"perusahaan": "BUMN", "posisi": "staf", "lokasi_kerja": "", "luar_negeri": False, "gaji": "",
                  "biaya_disebut": "Rp250.000", "saluran_lamaran": "WhatsApp", "kontak": [], "tautan": ["bit.ly/daftar-bumn"]},
        "rambu": [
            {"kode": "CATUT_PERUSAHAAN", "bukti": "Rekrutmen staf BUMN 2026", "alasan": "Mengatasnamakan BUMN lewat WA."},
            {"kode": "MINTA_BIAYA", "bukti": "Biaya administrasi Rp250.000", "alasan": "Ada biaya."},
            {"kode": "GAJI_TIDAK_WAJAR", "bukti": "gaji 50 juta per bulan", "alasan": "karangan"},
        ],
        "ringkasan": "Lowongan ini memiliki beberapa tanda penipuan.",
    }
    monkeypatch.setattr(config, "ai_available", lambda: True)
    monkeypatch.setattr(gemini, "analyze", lambda *a, **k: fake)
    r = analyzer.analyze(SCAM)
    kodes = {x["kode"]: x for x in r["rambu"]}
    assert r["mode"] == "aturan+ai"
    assert "CATUT_PERUSAHAAN" in kodes and kodes["CATUT_PERUSAHAAN"]["sumber"] == ["ai"]
    assert kodes["MINTA_BIAYA"]["sumber"] == ["aturan", "ai"]
    assert "GAJI_TIDAK_WAJAR" not in kodes                       # kutipan tidak ada di teks: ditolak
    assert any("diabaikan" in w for w in r["peringatan"])


def test_ai_free_email_claim_must_contain_free_domain():
    text = "Kirim lamaran ke Recruitment@augustea-intcrews.com sebelum akhir bulan."
    fake = {"teks_terbaca": text, "fakta": {}, "ringkasan": "",
            "rambu": [{"kode": "EMAIL_GRATISAN", "bukti": "Recruitment@augustea-intcrews.com", "alasan": "x"}]}
    r = analyzer.analyze(text, ai_data=fake)
    assert r["rambu"] == []
    assert any("diabaikan" in w for w in r["peringatan"])


def test_ai_failure_falls_back(monkeypatch):
    def boom(*a, **k):
        raise gemini.AIUnavailable("kuota habis")
    monkeypatch.setattr(config, "ai_available", lambda: True)
    monkeypatch.setattr(gemini, "analyze", boom)
    r = analyzer.analyze(SCAM)
    assert r["mode"] == "aturan" and r["peringatan"]
