"""Katalog rambu (tanda bahaya) lowongan kerja palsu.

Bobot ditetapkan di sini, bukan oleh AI, supaya skor bisa diaudit.
Rujukan ciri: imbauan Kemnaker tentang lowongan palsu (biaya, email/situs gratisan,
gaji tidak wajar, lokasi tidak sesuai) dan pola kasus yang diperiksa MAFINDO/TurnBackHoax.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rambu:
    kode: str
    judul: str
    bobot: int
    alasan: str
    hanya_ai: bool = False


KATALOG: dict[str, Rambu] = {r.kode: r for r in [
    Rambu("MINTA_BIAYA", "Meminta biaya", 50,
          "Perekrut resmi tidak memungut biaya pendaftaran, administrasi, pelatihan, seragam, medical, atau tiket."),
    Rambu("DEPOSIT_TUGAS", "Kerja online dengan misi atau deposit", 50,
          "Pola 'kerjakan misi, dapat komisi, lalu isi deposit' adalah modus penipuan yang berulang."),
    Rambu("TRAVEL_WAJIB", "Wajib memakai travel atau agen tertentu", 45,
          "Rekrutmen resmi tidak mewajibkan pelamar membeli tiket lewat agen perjalanan tertentu."),
    Rambu("MINTA_DATA_SENSITIF", "Meminta data sensitif lewat jalur tidak resmi", 30,
          "KTP, rekening, OTP, atau PIN yang dikirim lewat chat atau formulir tak resmi bisa disalahgunakan."),
    Rambu("TAUTAN_MENCURIGAKAN", "Tautan pendaftaran mencurigakan", 30,
          "Tautan pemendek atau hosting gratis sering dipakai untuk halaman pendaftaran palsu dan pencurian data."),
    Rambu("CATUT_PERUSAHAAN", "Mengatasnamakan perusahaan atau instansi besar", 25,
          "Nama perusahaan atau instansi besar dipakai, tetapi saluran lamarannya bukan saluran resmi mereka.",
          hanya_ai=True),
    Rambu("LUAR_NEGERI_TANPA_IZIN", "Kerja luar negeri tanpa keterangan izin penempatan", 15,
          "Penempatan kerja ke luar negeri harus lewat perusahaan penempatan berizin (P3MI). Lowongan ini tidak menyebut izinnya."),
    Rambu("KONTAK_PRIBADI", "Melamar lewat nomor pribadi", 15,
          "Lamaran diarahkan ke WhatsApp atau Telegram pribadi, bukan portal atau email resmi perusahaan."),
    Rambu("EMAIL_GRATISAN", "Memakai email gratisan", 15,
          "Perusahaan besar biasanya memakai email berdomain perusahaan, bukan Gmail atau Yahoo."),
    Rambu("GAJI_TIDAK_WAJAR", "Gaji atau komisi tidak wajar", 15,
          "Gaji sangat tinggi untuk pekerjaan tanpa syarat jelas adalah umpan yang sering dipakai."),
    Rambu("SYARAT_TERLALU_MUDAH", "Syarat terlalu mudah", 10,
          "Tanpa pengalaman, tanpa tes, langsung kerja: lowongan nyata hampir selalu punya proses seleksi."),
    Rambu("DESAKAN_WAKTU", "Mendesak agar cepat mendaftar", 10,
          "Desakan waktu dipakai agar korban tidak sempat memeriksa kebenaran lowongan."),
    Rambu("KONTRADIKSI", "Informasi saling bertentangan", 10,
          "Ada detail yang tidak cocok, misalnya lokasi interview berbeda dari alamat perusahaan atau posisi tidak jelas.",
          hanya_ai=True),
]}

LEVELS = (
    (50, "tinggi", "Risiko tinggi"),
    (20, "waspada", "Waspada"),
    (0, "rendah", "Belum ditemukan rambu utama"),
)


def level_for(score: int) -> tuple[str, str]:
    for minimum, kode, label in LEVELS:
        if score >= minimum:
            return kode, label
    return "rendah", LEVELS[-1][2]
