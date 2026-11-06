"""Bangun PDF proposal dari docs/proposal.html.

Nama file mengikuti rekomendasi panduan: docs/AIWIC2026_<NamaTim>_<NamaProduk>.pdf

    python scripts/evaluate.py --set pengembangan [--ai]
    python scripts/evaluate.py --set uji [--ai]
    python scripts/build_proposal.py

Isian tim (nama, anggota, tautan) dibaca dari docs/proposal-data.json. Angka evaluasi dibaca dari
docs/hasil-evaluasi-*.json, jadi proposal selalu memakai hasil evaluasi terakhir yang benar-benar dijalankan.
PDF dibuat dengan Microsoft Edge atau Chrome mode headless.
"""

import html
import re
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "backend"))

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge", "google-chrome", "chromium",
]
CAPTIONS = {
    "1-halaman-awal": "Halaman awal Lamarin: tempel teks atau unggah gambar lowongan",
    "2-hasil-pemeriksaan-ai": "Hasil pemeriksaan dengan AI: skor, ringkasan, dan rambu beserta kutipan buktinya",
}
LABELS = {"aturan": "Aturan saja", "ai_saja": "AI saja", "aturan_ai": "Aturan + AI (Lamarin)"}


def pct(x: float) -> str:
    return f"{x:.2f}"


def eval_rows() -> tuple[str, str, dict]:
    rows, info = [], {}
    for which in ("uji", "pengembangan"):
        path = DOCS / f"hasil-evaluasi-{which}.json"
        if not path.exists():
            continue
        r = json.loads(path.read_text(encoding="utf-8"))["ringkasan"]
        info[which] = r
        for key, label in LABELS.items():
            if key in r:
                m = r[key]
                rows.append(f"<tr><td>{label}</td><td>{which} ({r['jumlah']})</td><td class='n'>{pct(m['precision'])}</td>"
                            f"<td class='n'>{pct(m['recall'])}</td><td class='n'>{pct(m['f1'])}</td>"
                            f"<td class='n'>{pct(m['akurasi'])}</td></tr>")
    has_ai = any("aturan_ai" in r for r in info.values())
    note = ("Angka AI berasal dari menjalankan scripts/evaluate.py --ai dengan Gemini paket gratis."
            if has_ai else
            "Baris AI belum ada karena evaluasi dengan Gemini belum dijalankan (kunci API belum diatur). "
            "Jalankan scripts/evaluate.py --ai lalu bangun ulang proposal sebelum dikirim.")
    return "\n  ".join(rows) or "<tr><td colspan='6'>Belum ada hasil evaluasi.</td></tr>", note, info


def insight(info: dict) -> str:
    """Kalimat penjelas yang diturunkan langsung dari angka evaluasi (tanpa klaim tambahan)."""
    test = info.get("uji")
    if not test:
        return ""
    a = test["aturan"]
    text = (f"Pada set uji, aturan saja menangkap {a['tp']} dari {test['penipuan']} lowongan penipuan dan salah menandai "
            f"{a['fp']} dari {test['asli']} lowongan asli. Kebanyakan penipuan pada set uji tidak menulis biaya atau tautan "
            f"secara eksplisit, melainkan mencatut nama perusahaan atau instansi lalu mengarahkan ke \"link di bio\", "
            f"WhatsApp, atau DM; pola ini membutuhkan pemahaman konteks.")
    if "aturan_ai" in test:
        g = test["aturan_ai"]
        text += (f" Dengan AI, Lamarin menangkap {g['tp']} dari {test['penipuan']} penipuan dan salah menandai "
                 f"{g['fp']} dari {test['asli']} lowongan asli.")
    return text


def main() -> None:
    from app import config

    data_file = DOCS / "proposal-data.json"
    data = json.loads(data_file.read_text(encoding="utf-8")) if data_file.exists() else {}
    rows, note, info = eval_rows()
    dev = info.get("pengembangan", {})
    shots = sorted((DOCS / "img").glob("*.png")) + sorted((DOCS / "img").glob("*.jpg"))
    tokens = {
        "NAMA_TIM": data.get("nama_tim", "[Isi nama tim]"),
        "KETUA": data.get("ketua", "[Isi nama ketua]"),
        "ANGGOTA": data.get("anggota", "[Isi nama anggota]"),
        "INSTANSI": data.get("instansi", "[Isi sekolah/universitas/komunitas]"),
        "KATEGORI": data.get("kategori", "[SMA/SMK/sederajat atau Mahasiswa/Umum]"),
        "KONTAK": data.get("kontak", "[Isi email/telepon ketua]"),
        "GITHUB": data.get("github", "[Isi URL repository]"),
        "DEPLOY": data.get("deploy", "[Isi URL Vercel]"),
        "TAG": data.get("tag", "v1.0-submission (isi commit hash)"),
        "MODEL": config.GEMINI_MODEL,
        "DEV_N": str(dev.get("jumlah", "-")),
        "TEST_N": str(info.get("uji", {}).get("jumlah", "-")),
        "DEV_RECALL": (f"{dev['aturan']['tp']} dari {dev['penipuan']}" if dev else "sebagian"),
        "EVAL_ROWS": rows,
        "EVAL_NOTE": html.escape(note),
        "EVAL_INSIGHT": html.escape(insight(info)),
        "SCREENSHOTS": "\n".join(
            f'<img class="shot" src="img/{p.name}" alt="Tangkapan layar Lamarin">'
            f'<p class="caption">Gambar {i}. {html.escape(CAPTIONS.get(p.stem, "Tampilan Lamarin"))}</p>'
            for i, p in enumerate(shots, start=2)) or "<p>[Tambahkan tangkapan layar ke docs/img/]</p>",
    }
    src = (DOCS / "proposal.html").read_text(encoding="utf-8")
    already_html = {"EVAL_ROWS", "SCREENSHOTS", "EVAL_NOTE", "EVAL_INSIGHT"}
    for k, v in tokens.items():
        src = src.replace("{{" + k + "}}", v if k in already_html else html.escape(v))
    built = DOCS / "proposal.build.html"
    built.write_text(src, encoding="utf-8")

    browser = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if not browser:
        sys.exit(f"Edge/Chrome tidak ditemukan. Buka {built} di peramban lalu cetak ke PDF (A4).")
    team = re.sub(r"[^0-9A-Za-z]", "", data.get("nama_tim", "NamaTim").title()) or "NamaTim"
    out = (DOCS / f"AIWIC2026_{team}_Lamarin.pdf").resolve()
    if out.exists():
        out.unlink()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        # Profil terpisah supaya tidak menumpang ke jendela Edge/Chrome yang sedang terbuka.
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                        f"--user-data-dir={profile}", f"--print-to-pdf={out}", built.resolve().as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        for _ in range(60):
            if out.exists() and out.stat().st_size > 0:
                break
            time.sleep(0.5)
    # proposal.build.html dibiarkan untuk pratinjau; file ini diabaikan git.
    if not out.exists():
        sys.exit("PDF gagal dibuat. Buka docs/proposal.html di peramban lalu cetak ke PDF (A4).")
    print(f"Proposal: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
