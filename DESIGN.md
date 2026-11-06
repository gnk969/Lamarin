# DESIGN.md: Lamarin

**Design Read:** alat pemeriksa satu halaman untuk pencari kerja muda di Bali, dengan bahasa visual
editorial yang tenang, minimalis, dan elegan. Dial: ENERGY 1 / RHYTHM 1 / MOTION 1.

## Referensi (inspirasi, bukan disalin)

- Dribbble: "AskSilver: AI Scam-Checking Platform" oleh Goodspeed Studio,
  https://dribbble.com/shots/27233741-AskSilver-AI-Scam-Checking-Platform
  Diambil: latar putih gading, judul serif besar, satu kartu input bertab (teks / gambar) sebagai pusat halaman,
  tombol utama hitam. Ilustrasi tokoh dan logo media pada referensi tidak dipakai.

## Identitas

- **Motif rambu lalu lintas:** setiap tanda bahaya ditampilkan sebagai rambu segitiga kecil. Warnanya mengikuti
  rambu jalan di Indonesia: kuning untuk waspada, merah untuk risiko tinggi. Ini menghubungkan nama produk
  dengan fitur utamanya (daftar rambu beserta buktinya).
- **Tidak ada label hijau "aman".** Hasil terendah ditulis "Belum ditemukan rambu utama", karena alat ini
  tidak bisa menjamin lowongan asli.
- **Logo:** sementara berupa rambu segitiga dan nama produk dalam huruf Newsreader (placeholder).

## Warna (netral + 2 warna rambu)

| Peran | Terang | Gelap | Dipakai untuk |
|---|---|---|---|
| Kertas | `#F7F4EE` | `#141310` | latar |
| Permukaan | `#FFFFFF` | `#1E1C18` | kartu |
| Tinta | `#16140F` | `#F2EEE6` | teks, tombol utama |
| Rambu kuning | `#E9A100` | `#F2B833` | level waspada, isi rambu segitiga |
| Rambu merah | `#B8321B` | `#FF7A61` | level risiko tinggi, rambu berbobot besar |

Teks di atas kuning selalu tinta gelap.

## Tipografi

- **Newsreader** (serif) untuk judul dan angka skor: nada editorial yang tenang dan dapat dipercaya.
- **Public Sans** untuk antarmuka: huruf yang dirancang untuk layanan publik, netral dan jelas.

## Aturan komponen

- Radius 12px untuk kartu, 8px untuk input dan tombol. Tanpa bentuk pil kecuali penanda sumber (Aturan / AI).
- Bayangan hanya pada kartu input utama (fokus halaman).
- Gerak: hanya hover, fokus, dan indikator muat.
- Tema terang bawaan, tema gelap lewat tombol.
