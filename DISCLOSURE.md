# AI & Technology Disclosure (Lampiran C)

| Komponen | Isi |
|---|---|
| Nama Produk | Lamarin |
| Framework / Frontend | HTML, CSS, JavaScript (ES modules), tanpa framework. Tesseract.js 5.1.1 (CDN jsDelivr) untuk membaca teks gambar di peramban saat AI tidak aktif |
| Backend / Runtime | Python 3.11+, FastAPI, Uvicorn, httpx |
| Database / Storage | Tidak ada database. Masukan pengguna tidak disimpan. Data uji di folder `data/` (JSON) |
| Hosting / Deployment | Vercel paket Hobby gratis (`vercel.json`). URL dicantumkan di README setelah deploy |
| AI Model / API / Method | Google Gemini API paket gratis, model `gemini-3.5-flash-lite` (dapat diganti lewat `GEMINI_MODEL`), endpoint REST `generateContent` dengan keluaran JSON terstruktur (JSON schema). Ditambah mesin aturan berbasis pola teks (regex) buatan tim |
| Peran AI dalam Produk | (1) Membaca teks dari tangkapan layar lowongan. (2) Mengekstrak fakta lowongan (perusahaan, posisi, gaji, biaya, kontak, tautan). (3) Menemukan rambu kontekstual yang sulit ditangkap aturan, misalnya pencatutan nama perusahaan dan informasi yang saling bertentangan. Setiap rambu dari AI wajib mengutip teks lowongan dan diverifikasi server; skor dihitung dari bobot tetap, bukan oleh AI |
| Dataset / Data Source | `data/contoh_penipuan.json`: kutipan lowongan penipuan dari artikel pemeriksa fakta (tautan sumber per item). `data/contoh_asli.json`: kutipan lowongan dari situs karier resmi atau situs pemerintah (tautan sumber per item). Dipakai untuk evaluasi dan contoh, bukan untuk melatih model |
| Open-source Libraries | fastapi, uvicorn, pydantic, httpx, pytest (Python); tesseract.js (JavaScript) |
| Template / Boilerplate | Tidak ada |
| AI Coding Assistant | Claude Code (Anthropic) dipakai untuk membantu riset, menulis kode awal, mengumpulkan data uji dari sumber publik, dan menyusun dokumentasi. Tim bertanggung jawab memahami, menguji, dan mempertahankan seluruh kode |
| Pre-existing Components | Tidak ada; dibuat untuk kompetisi |
| Third-party Assets / Credits | Google Fonts: Newsreader, Public Sans (SIL Open Font License). Inspirasi tampilan: "AskSilver: AI Scam-Checking Platform" oleh Goodspeed Studio di Dribbble (tidak disalin). Ciri lowongan palsu merujuk imbauan Kemnaker dan artikel MAFINDO/TurnBackHoax |

**Privasi:** teks atau gambar yang diperiksa tidak disimpan di server. Bila AI aktif, isinya dikirim ke Gemini API.
Pada paket gratis, Google menyatakan konten dapat dipakai untuk meningkatkan produknya; hal ini ditampilkan di halaman aplikasi.

Pernyataan: Kami menyatakan bahwa informasi di atas benar dan lengkap. Kami bertanggung jawab atas penggunaan teknologi,
source code, data, library, API, model AI, dan aset yang digunakan pada produk.
