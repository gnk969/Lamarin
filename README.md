# Lamarin

## Description
Lamarin adalah aplikasi web untuk memeriksa lowongan kerja sebelum melamar. Pengguna menempel teks
atau mengunggah tangkapan layar lowongan, lalu aplikasi menandai **rambu** (tanda bahaya penipuan)
beserta kutipan buktinya, memberi skor risiko, dan menyarankan langkah aman.

Tema lomba: **Bali Smart Society** (layanan dan perlindungan masyarakat), dengan sasaran pencari kerja muda
dan calon pekerja migran di Bali.

## Problem & Target User
- **Pengguna:** pencari kerja muda di Bali, calon pekerja kapal pesiar dan luar negeri, serta keluarga yang membantu memeriksa tawaran kerja.
- **Masalah:** lowongan palsu tersebar di media sosial dan WhatsApp, meminta biaya atau data pribadi, dan pada kasus terburuk berujung perdagangan orang. Contoh di Bali: puluhan ABK korban TPPO di Pelabuhan Benoa direkrut lewat Facebook ([detikBali](https://www.detik.com/bali/hukum-dan-kriminal/d-8353640/puluhan-abk-jadi-korban-perdagangan-orang-pecatan-polisi-diadili)). Pemeriksa fakta mencatat poster lowongan palsu yang kini dibuat dengan AI ([TurnBackHoax, 5 Nov 2026](https://turnbackhoax.id/articles/37376-penipuan-tautan-pendaftaran-staf-sekolah-rakyat-tahun-2026)).
- Pengguna jarang tahu ciri-ciri lowongan palsu, dan memeriksa satu per satu ke situs resmi butuh waktu.

## Key Features
1. **Periksa teks**: tempel isi lowongan dari WhatsApp, Facebook, atau situs mana pun.
2. **Periksa gambar**: unggah, seret, atau tempel (Ctrl+V) tangkapan layar poster lowongan.
3. **Rambu dengan bukti**: setiap tanda bahaya menampilkan kutipan kalimat lowongan yang memicunya, sumbernya (Aturan / AI), dan alasannya.
4. **Skor risiko 0-100** dengan tiga level: Risiko tinggi, Waspada, Belum ditemukan rambu utama. Tidak ada label "aman".
5. **Fakta yang terbaca** (perusahaan, posisi, gaji, biaya, kontak, tautan) dan **langkah aman** sesuai rambu.
6. **Contoh kasus nyata** dari artikel cek fakta dan situs karier resmi, dengan tautan sumber.

## Tech Stack
- Backend: Python 3.11+, FastAPI, Uvicorn, httpx
- Frontend: HTML, CSS, JavaScript tanpa framework; Tesseract.js (pembaca teks gambar di peramban saat AI tidak aktif)
- AI: Google Gemini API paket gratis (`gemini-3.5-flash-lite`)
- Database: tidak ada (masukan tidak disimpan)
- Hosting: Vercel paket Hobby gratis (`vercel.json`, titik masuk `api/index.py`)

## AI Implementation
| Tahap | Metode | Input | Output |
|---|---|---|---|
| Baca gambar | **Gemini (multimodal)** | tangkapan layar | teks lowongan |
| Ekstraksi fakta | **Gemini, JSON schema** | teks lowongan | perusahaan, posisi, gaji, biaya, kontak, tautan |
| Rambu kontekstual | **Gemini, JSON schema** | teks lowongan | rambu dari katalog tetap + kutipan bukti + alasan (mis. mencatut perusahaan besar, informasi bertentangan) |
| Rambu pola | aturan (regex) | teks lowongan | 11 rambu: biaya, deposit, travel wajib, data sensitif, tautan mencurigakan, kontak pribadi, email gratisan, gaji tidak wajar, syarat terlalu mudah, desakan waktu, luar negeri tanpa izin |
| Verifikasi | kode | kutipan AI vs teks | rambu AI tanpa kutipan yang cocok ditolak |
| Skor | bobot tetap | rambu unik | skor 0-100 dan level |

**Mengapa AI diperlukan:** poster lowongan berupa gambar, kalimatnya bebas, dan banyak penipuan baru terlihat dari konteks
(nama BUMN tetapi lamaran lewat Gmail; lokasi interview berbeda dari kantor). Aturan saja tidak bisa membaca gambar
dan melewatkan pola yang tidak tertulis persis.

**Penanganan kegagalan:** bila kunci API kosong, kuota gratis habis, jaringan putus, atau jawaban AI tidak valid,
pemeriksaan tetap berjalan dengan aturan saja dan halaman menampilkan peringatan. Gambar tetap bisa dibaca di
peramban dengan Tesseract.js.

## Architecture / Data Flow
```
Pengguna -> Frontend (teks / gambar)
         -> [tanpa AI: Tesseract.js membaca gambar di peramban]
         -> FastAPI POST /api/periksa
              -> rules.py      (rambu pola)
              -> gemini.py     (baca gambar, ekstrak fakta, rambu kontekstual)   [opsional]
              -> analyzer.py   (verifikasi kutipan AI, gabung rambu, skor bobot tetap, langkah aman)
         <- JSON hasil -> tampilan rambu, skor, fakta, langkah aman
```

## Evaluation
Semua data dari sumber nyata (tidak ada data buatan), dengan tautan sumber per item:

| Set | Penipuan (artikel pemeriksa fakta) | Asli (situs karier resmi / go.id) | Kegunaan |
|---|---|---|---|
| Pengembangan | `data/contoh_penipuan.json` (27) | `data/contoh_asli.json` (25) | menyusun aturan |
| Uji (terpisah) | `data/uji_penipuan.json` (15) | `data/uji_asli.json` (12) | uji buta, tidak dipakai menyetel aturan |

```bash
python scripts/evaluate.py --set uji            # aturan saja
python scripts/evaluate.py --set uji --ai       # + AI saja dan aturan + AI (butuh GEMINI_API_KEY)
python scripts/build_proposal.py                # angka terbaru masuk ke docs/proposal.pdf
```

Hasil terakhir (6 Nov 2026, model `gemini-3.5-flash-lite`, ambang skor >= 20):

| Set | Versi | Precision | Recall | F1 | Akurasi |
|---|---|---|---|---|---|
| Uji (buta, 27) | Aturan saja | 1.00 | 0.07 | 0.12 | 0.48 |
| Uji (buta, 27) | AI saja | 0.90 | 0.60 | 0.72 | 0.74 |
| Uji (buta, 27) | **Aturan + AI** | **0.91** | **0.67** | **0.77** | **0.78** |
| Pengembangan (52) | Aturan saja | 1.00 | 0.44 | 0.61 | 0.71 |
| Pengembangan (52) | AI saja | 0.94 | 0.63 | 0.76 | 0.79 |
| Pengembangan (52) | Aturan + AI | 0.95 | 0.67 | 0.78 | 0.81 |

Pada uji buta, AI menaikkan penipuan yang tertangkap dari 1 menjadi 10 dari 15, dengan 1 lowongan asli salah
ditandai. Catatan jujur:
- Jawaban AI sedikit berbeda antar-jalan walau temperature 0. Dua kali uji buta memberi angka gabungan yang sama,
  tetapi lowongan yang salah berbeda.
- Pemeriksaan "email gratisan harus benar-benar memuat domain gratisan" (`analyzer._claim_matches`) ditambahkan
  setelah melihat salah tuduh pada uji buta pertama. Ini aturan kebenaran fakta, bukan penyetelan bobot, tetapi
  set uji ini tidak lagi sepenuhnya buta untuk pemeriksaan tersebut. Set uji baru perlu dikumpulkan untuk angka akhir.
- 5 penipuan masih lolos, umumnya poster yang hanya mencatut nama instansi dan mengarahkan ke tautan tanpa biaya
  atau kontak pribadi di teksnya.

Detail per item, termasuk jawaban AI mentah: `docs/hasil-evaluasi-*.json`.

## Installation / Run Instructions
1. Pasang Python 3.11 atau lebih baru.
2. Salin `.env.example` menjadi `.env`, lalu isi `GEMINI_API_KEY` (gratis dari https://aistudio.google.com). Tanpa kunci, aplikasi berjalan dalam mode aturan.
3. Jalankan:
   ```bash
   pip install -r requirements.txt
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
   Di Windows bisa klik dua kali `jalankan.bat`.
4. Buka http://127.0.0.1:8000
5. Tes: `python -m pytest backend/tests`

## Deployment URL
[Isi URL Vercel setelah deploy]

Deploy gratis tanpa kartu kredit di Vercel: https://vercel.com > Add New > Project > import repo ini > di Environment Variables
isi `GEMINI_API_KEY` (dan `GEMINI_MODEL=gemini-3.5-flash-lite`) > Deploy. Vercel membaca `vercel.json`.
Alternatif: `render.yaml` untuk Render (paket gratis Render meminta kartu kredit untuk web service).

## Demo Account
Tidak perlu login.

## Known Limitations
- Rambu adalah indikator, bukan bukti. Lowongan tanpa rambu tetap perlu dicek ke saluran resmi.
- Set uji masih kecil; angka evaluasi belum mewakili semua jenis lowongan.
- Belum ada pengecekan otomatis ke daftar perusahaan penempatan pekerja migran (P3MI) resmi.
- Pembacaan gambar tanpa AI (Tesseract.js) kurang akurat untuk poster bergaya rumit.
- Paket gratis Gemini punya batas kuota, dan Google dapat memakai konten paket gratis untuk meningkatkan produknya.
- Di hosting gratis, pemeriksaan pertama setelah lama tidak dipakai bisa sedikit lebih lambat (cold start).
- Gambar besar diperkecil di peramban (sisi terpanjang 2000 px) sebelum dikirim, karena batas ukuran permintaan hosting.

## Third-party Resources / Credits
- Google Gemini API; Tesseract.js (Apache-2.0); FastAPI, Uvicorn, Pydantic, httpx, pytest.
- Google Fonts: Newsreader, Public Sans (SIL Open Font License).
- Data uji: kutipan dari artikel pemeriksa fakta (MAFINDO/TurnBackHoax dan lainnya) dan situs karier resmi, dengan tautan sumber per item.
- Ciri lowongan palsu merujuk imbauan Kemnaker.
- Inspirasi tampilan: "AskSilver: AI Scam-Checking Platform" oleh Goodspeed Studio (Dribbble), tidak disalin.

## Team Members
[Isi nama anggota tim dan perannya]
