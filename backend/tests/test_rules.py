"""Tes unit aturan. Kalimat di sini adalah kalimat uji buatan untuk memeriksa tiap aturan,
bukan data evaluasi (data evaluasi asli ada di folder data/)."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RAMBU_AI"] = "off"
os.environ["RAMBU_CEK_TAUTAN"] = "off"

from app import analyzer, rules  # noqa: E402
from app.rambu import KATALOG, level_for  # noqa: E402


def kodes(text):
    return {t.kode for t in rules.detect(text)}


def test_fee_detected_and_negation_ignored():
    assert "MINTA_BIAYA" in kodes("Peserta wajib transfer biaya pendaftaran Rp150.000 ke rekening panitia.")
    assert "MINTA_BIAYA" in kodes("Biaya seragam dan medical Rp 750 ribu dibayar saat interview.")
    assert "MINTA_BIAYA" not in kodes("Seluruh proses rekrutmen tidak dipungut biaya pendaftaran apa pun.")
    assert "MINTA_BIAYA" not in kodes("Rekrutmen ini GRATIS tanpa biaya pendaftaran.")
    # negasi di baris sebelumnya tidak boleh menutupi permintaan biaya (kasus dari uji OCR)
    assert "MINTA_BIAYA" in kodes("Gaji 30 juta tanpa pengalaman\nBiaya pendaftaran Rp500.000")


def test_task_deposit_scam():
    assert "DEPOSIT_TUGAS" in kodes("Kerja online cukup like dan follow, komisi Rp50.000 per misi.")
    assert "DEPOSIT_TUGAS" in kodes("Untuk lanjut ke level berikutnya silakan deposit 200rb.")


def test_travel_agent_required():
    assert "TRAVEL_WAJIB" in kodes("Peserta interview wajib menggunakan travel yang sudah kami tunjuk.")


def test_sensitive_data():
    assert "MINTA_DATA_SENSITIF" in kodes("Kirim kode OTP yang masuk ke HP Anda untuk verifikasi.")
    assert "MINTA_DATA_SENSITIF" in kodes("Kirim foto KTP dan nomor rekening via WhatsApp admin.")
    assert "MINTA_DATA_SENSITIF" not in kodes("Berkas: CV, fotokopi KTP, ijazah terakhir, dikirim lewat portal karier.")


def test_suspicious_links():
    assert "TAUTAN_MENCURIGAKAN" in kodes("Daftar di bit.ly/loker-bumn-2026 sekarang")
    assert "TAUTAN_MENCURIGAKAN" in kodes("Link: https://daftaar0nline3[dot]akijai35[dot]workers[dot]dev/")
    assert "TAUTAN_MENCURIGAKAN" not in kodes("Lamar melalui https://karirhub.kemnaker.go.id")


def test_contacts_and_email():
    assert "KONTAK_PRIBADI" in kodes("Info lebih lanjut hubungi WA 0812-3456-7xxx")
    assert "KONTAK_PRIBADI" in kodes("Pendaftaran via WA 0812-3456-7xxx sekarang.")
    assert "KONTAK_PRIBADI" not in kodes("Jam kerja 08.00 - 17.00 WITA, Senin sampai Jumat.")
    assert "EMAIL_GRATISAN" in kodes("Kirim lamaran ke hrd.pertamina.rekrut@gmail.com")
    assert "EMAIL_GRATISAN" not in kodes("Kirim lamaran ke recruitment@hotelbali.co.id")


def test_salary_and_overseas():
    assert "GAJI_TIDAK_WAJAR" in kodes("Gaji 25 juta per bulan tanpa pengalaman.")
    assert "GAJI_TIDAK_WAJAR" in kodes("Penghasilan Rp500.000 per hari, kerja dari rumah.")
    assert "GAJI_TIDAK_WAJAR" not in kodes("Gaji sesuai UMK Badung.")
    assert "LUAR_NEGERI_TANPA_IZIN" in kodes("Dibutuhkan crew kapal pesiar, berangkat bulan depan.")
    assert "LUAR_NEGERI_TANPA_IZIN" not in kodes("Penempatan Jepang melalui P3MI berizin, terdaftar di KP2MI.")


def test_multiline_payment_and_false_links():
    text = ("Untuk Reservasinya paket sudah termasuk:\n– Tiket PP\n– Hotel\nMohon selesaikan pembayaran melalui "
            "transfer\nBANK X\nTotal : Rp 3.920.887\nKonfirmasikan transfer.kirim via whatsapp ke nomor ini.")
    assert {"MINTA_BIAYA", "TRAVEL_WAJIB"} <= kodes(text)
    assert rules.domains_in("Konfirmasikan transfer.kirim via whatsapp") == []
    assert rules.domains_in("daftar di bit.ly/abc") == ["bit.ly/abc"]


def test_payment_instruction_and_packages():
    assert "MINTA_BIAYA" in kodes("Mohon selesaikan pembayaran melalui transfer. Total : Rp 3.920.887")
    assert "MINTA_BIAYA" in kodes("Tersedia dana talang sistem potong gaji.")
    assert "TRAVEL_WAJIB" in kodes("Reservasi paket sudah termasuk tiket PP dan hotel.")
    assert "DESAKAN_WAKTU" in kodes("Batas waktu pembayaran 45 menit.")


def test_new_patterns():
    assert "MINTA_DATA_SENSITIF" in kodes("Silakan kirimkan foto hanya mengenakan pakaian dalam untuk ukuran seragam.")
    assert "DEPOSIT_TUGAS" in kodes("Tugas LIKE dan SUBSCRIBE channel Youtube, pekerjaan sampingan.")
    assert "GAJI_TIDAK_WAJAR" in kodes("Dapat gaji 12 juta perminggu.")
    assert "GAJI_TIDAK_WAJAR" in kodes("Kami menjamin pendapatan stabil minimal 300.000 IDR per hari.")
    assert "TAUTAN_MENCURIGAKAN" in kodes("Daftar di https://lowongankerjadikantor[dot]jesdr[dot]com/")
    assert "TAUTAN_MENCURIGAKAN" not in kodes("Daftar di https://rekrutmen.pln.co.id")
    assert "KONTAK_PRIBADI" in kodes("Pendaftaran langsung masuk Dm.")


def test_level_thresholds():
    assert level_for(0)[0] == "rendah"
    assert level_for(20)[0] == "waspada"
    assert level_for(50)[0] == "tinggi"
    assert all(r.bobot > 0 for r in KATALOG.values())


def test_analyzer_rules_only_score():
    r = analyzer.analyze("Lowongan crew kapal pesiar. Biaya medical Rp2 juta transfer ke rekening. Hubungi WA 081234567xxx",
                         use_ai=False)
    assert r["mode"] == "aturan"
    assert r["level"] == "tinggi"
    assert {x["kode"] for x in r["rambu"]} >= {"MINTA_BIAYA", "KONTAK_PRIBADI", "LUAR_NEGERI_TANPA_IZIN"}
    assert r["skor"] == min(100, sum(x["bobot"] for x in r["rambu"]))


def test_evidence_check():
    text = "Kirim lamaran ke hrd.rekrut@gmail.com paling lambat besok."
    assert analyzer.evidence_in_text("hrd.rekrut@gmail.com", text)
    assert not analyzer.evidence_in_text("wajib bayar Rp500.000", text)


def test_snippet_single_line_poster_starts_near_trigger():
    text = ("LOWONGAN KERJA HOTEL BINTANG 5 DUBAI Posisi: Housekeeping, Cook Helper, Laundry Gaji: Rp 25.000.000 / bulan "
            "Tanpa pengalaman, lulusan SMP bisa Biaya proses visa & tiket Rp 4.500.000 transfer ke rekening a/n agen")
    biaya = next(t for t in rules.detect(text) if t.kode == "MINTA_BIAYA")
    assert not biaya.bukti.startswith("LOWONGAN")
    assert "Biaya proses visa" in biaya.bukti
