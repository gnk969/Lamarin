# Kesiapan tahapan lomba (dicocokkan dengan Panduan Peserta, hlm. 3-11)

Status: [x] siap, [ ] perlu dikerjakan tim, [~] sebagian.

## Tahap 1: Registrasi & Submission (4 komponen wajib)

| Komponen | Status | Lokasi / catatan |
|---|---|---|
| Proposal PDF A4, maks 5 halaman isi di luar cover & lampiran | [~] | `docs/proposal.pdf` (dari `docs/proposal.html`). Isi nama tim, anggota, instansi, kontak ketua, dan URL deploy |
| Repository GitHub | [~] | Kode siap. Tim membuat repo di GitHub lalu push (lihat README bagian GitHub) |
| URL website/MVP aktif | [ ] | Deploy gratis lewat Render (`render.yaml`). Isi `GEMINI_API_KEY` di dashboard Render |
| AI & Technology Disclosure | [x] | `DISCLOSURE.md` |
| README minimal (Lampiran B) | [~] | `README.md`. Isi Deployment URL dan Team Members |
| `.env.example` tanpa secret | [x] | `.env.example` |
| Riwayat commit dapat diverifikasi | [x] | Commit lokal sudah ada; lanjutkan commit kecil dan sering |
| Version locking | [~] | Tag `v1.0-submission` dibuat lokal. Pindahkan ke commit terakhir sebelum deadline: `git tag -f v1.0-submission` lalu `git push -f origin v1.0-submission`. Catat commit hash di formulir |
| Demo account | [x] | Tidak perlu login |

### Technical gate (hlm. 7) dan cara memenuhinya
- Identitas & komposisi peserta: diisi tim.
- Proposal lengkap & terbaca: `docs/proposal.pdf`.
- Repository dapat diakses: public, atau private dengan akses baca untuk akun GitHub panitia.
- Website dapat diakses: URL Render. Paket gratis Render tidur bila tidak dipakai (bangun sekitar 30-60 detik); buka URL sebelum jadwal penjurian atau pakai monitor uptime gratis.
- Fungsi utama dapat diuji: juri cukup menempel teks atau mengunggah gambar lowongan.
- AI terintegrasi secara material: Gemini membaca gambar, mengekstrak fakta, dan menambah rambu kontekstual. Tanpa kunci API, aplikasi tetap jalan dalam mode aturan; untuk penjurian, **kunci API harus aktif**.

## Tahap 2: Final Submission (bila masuk Top 5 kategori)

| Komponen | Status | Yang perlu dilakukan |
|---|---|---|
| Website final aktif | [ ] | Deploy ulang setelah perbaikan, uji ulang dari perangkat lain |
| GitHub final, tag `v2.0-final` | [ ] | `git tag v2.0-final && git push origin v2.0-final` |
| Video demo maks 5 menit, 16:9, minimal 1080p, minimal 50% demo produk | [ ] | Ikuti naskah di bawah. Subtitle disarankan |
| Clean-start demo: buka aplikasi, input, proses, output | [x] | Alur aplikasi mendukung; mulai dari halaman kosong |
| Disclosure final | [ ] | Perbarui `DISCLOSURE.md` bila model/API/stack berubah |
| Catatan improvement Tahap 1 ke Tahap 2 | [ ] | Tulis di `docs/IMPROVEMENT.md` (daftar perubahan + alasan) |
| Technical verification | [ ] | Semua anggota latihan menjawab daftar pertanyaan di bawah |

### Naskah video (struktur rekomendasi panduan hlm. 8)

| Waktu | Bagian | Isi |
|---|---|---|
| 0:00-0:30 | Problem | Kasus perekrutan lewat media sosial yang berujung TPPO di Pelabuhan Benoa; lowongan palsu memakai poster buatan AI |
| 0:30-1:00 | Solution | Lamarin: tempel teks atau unggah gambar, dapatkan rambu bahaya beserta buktinya |
| 1:00-3:30 | Product demo | (1) Buka aplikasi dari awal. (2) Unggah tangkapan layar lowongan penipuan nyata, tunjukkan rambu dan kutipan bukti. (3) Tempel lowongan resmi dari situs karier, tunjukkan hasil rendah. (4) Matikan internet/AI untuk menunjukkan mode aturan tetap jalan |
| 3:30-4:30 | AI & architecture | Diagram: input, Gemini (baca gambar, ekstrak fakta, rambu kontekstual), aturan, verifikasi kutipan, skor bobot tetap. Tunjukkan tabel evaluasi tiga versi |
| 4:30-5:00 | Impact & future | Keterbatasan, rencana: cek daftar P3MI resmi, ekstensi peramban, bot WhatsApp |

### Persiapan technical verification (contoh pertanyaan dari panduan hlm. 9)

| Pertanyaan juri | Jawaban & lokasi kode |
|---|---|
| Tunjukkan kode yang memanggil AI | `backend/app/gemini.py`, fungsi `analyze` |
| Model/API apa dan mengapa | Gemini paket gratis: bisa membaca gambar dan memberi JSON terstruktur tanpa biaya; Flash-Lite cepat untuk pemeriksaan interaktif |
| Jalankan dengan input berbeda dari video | Siapkan 3 lowongan baru dari TurnBackHoax dan 3 dari situs karier resmi yang tidak ada di set uji |
| Bagaimana bila AI/API gagal | `backend/app/analyzer.py`: galat AI ditangkap, hasil tetap dari aturan dengan pesan peringatan; diuji di `backend/tests/test_api.py::test_ai_failure_falls_back` |
| Data apa yang dikirim ke model, bagaimana privasinya | Hanya teks/gambar lowongan yang diperiksa; tidak disimpan; pengguna diberi tahu bahwa paket gratis Gemini dapat memakai konten |
| Bagaimana mencegah AI mengarang | Setiap rambu AI wajib mengutip teks; `evidence_in_text` menolak kutipan yang tidak ada; skor dari bobot tetap di `backend/app/rambu.py` |
| Bagian yang sudah ada sebelumnya | Tidak ada; seluruhnya dibuat untuk kompetisi |
