"""Verifikasi sumber: domain pendaftaran harus cocok dengan instansi/perusahaan yang disebut."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RAMBU_AI"] = "off"

from app import analyzer, sumber  # noqa: E402

RESMI = ("Kementerian Kesehatan RI membuka Rekrutmen Tenaga Kesehatan 2026. Unggah scan KTP dan ijazah melalui "
         "link pendaftaran https://s.kemkes.go.id/RekrutmenNakes2026. Pendaftaran ditutup 30 November 2026, kuota terbatas.")


def test_official_government_domain_cancels_context_flags():
    r = analyzer.analyze(RESMI, use_ai=False)
    assert r["sumber"]["status"] == "resmi"
    assert r["level"] == "rendah" and r["rambu"] == []
    assert r["sumber"]["rambu_dibatalkan"]


def test_official_domain_with_ai_impersonation_flag_is_cancelled():
    fake = {"teks_terbaca": RESMI, "fakta": {"perusahaan": "Kementerian Kesehatan"}, "ringkasan": "",
            "rambu": [{"kode": "CATUT_PERUSAHAAN", "bukti": "Kementerian Kesehatan RI membuka Rekrutmen", "alasan": "x"}]}
    r = analyzer.analyze(RESMI, ai_data=fake)
    assert all(x["kode"] != "CATUT_PERUSAHAAN" for x in r["rambu"])


def test_impersonation_via_shortener_is_flagged_by_rules():
    t = "REKRUTMEN PEGAWAI KEMENTERIAN KESEHATAN RI 2026. Daftar lewat bit.ly/rekrutmen-kemenkes-2026 sekarang."
    r = analyzer.analyze(t, use_ai=False)
    assert r["sumber"]["status"] == "tidak_cocok"
    assert {"CATUT_PERUSAHAAN", "TAUTAN_MENCURIGAKAN"} <= {x["kode"] for x in r["rambu"]}


def test_official_link_does_not_hide_fee_or_personal_number():
    t = ("Kemenkes buka lowongan. Daftar di https://s.kemkes.go.id/daftar lalu konfirmasi ke WA admin 081299817766 "
         "dan bayar biaya administrasi Rp150.000.")
    r = analyzer.analyze(t, use_ai=False)
    assert r["sumber"]["status"] == "campuran"
    assert {"MINTA_BIAYA", "KONTAK_PRIBADI"} <= {x["kode"] for x in r["rambu"]}
    assert r["level"] == "tinggi"


def test_lookalike_domain_is_not_official():
    assert sumber.verify("Lowongan Kemenkes, daftar di https://kemkes-go.id/daftar").status == "tidak_cocok"
    assert sumber.verify("Lowongan Kemenkes, daftar di https://kemkes.go.id.daftar-online.xyz/a").status == "tidak_cocok"


def test_common_words_are_not_org_claims():
    h = sumber.verify("Mampu bekerja mandiri, siap perjalanan dinas, merayakan kemenangan. Kirim CV ke hr@kopikita.com")
    assert h.instansi == "" and h.status == "netral"
