"""Evaluasi Lamarin pada set uji berlabel dari sumber nyata.

    python scripts/evaluate.py          # aturan saja (gratis, tanpa jaringan)
    python scripts/evaluate.py --ai     # + "AI saja" dan "aturan + AI" (memakai GEMINI_API_KEY)

Dua set data (keduanya dari sumber nyata, dengan tautan sumber per item):
- set "pengembangan": data/contoh_penipuan.json + data/contoh_asli.json
  (dipakai saat menyusun dan menyetel aturan, jadi hasilnya cenderung optimistis)
- set "uji": data/uji_penipuan.json + data/uji_asli.json
  (dikumpulkan terpisah dan TIDAK dipakai untuk menyetel aturan; angka utama untuk proposal)
Positif = penipuan. Prediksi positif bila level "waspada" atau "tinggi" (skor >= 20).
Hasil per item disimpan ke docs/hasil-evaluasi-<set>.json supaya bisa diperiksa ulang.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


FILES = {"pengembangan": ("contoh_penipuan.json", "contoh_asli.json"),
         "uji": ("uji_penipuan.json", "uji_asli.json")}


def load(which):
    items = []
    scam, real = FILES[which]
    for fname, label in ((scam, 1), (real, 0)):
        path = ROOT / "data" / fname
        if not path.exists():
            continue
        for x in json.loads(path.read_text(encoding="utf-8")):
            items.append({"id": x["id"], "label": label, "teks": x["teks_lowongan"], "url": x["url"]})
    return items


def metrics(rows, key):
    tp = sum(1 for r in rows if r["label"] == 1 and r[key] >= 20)
    fn = sum(1 for r in rows if r["label"] == 1 and r[key] < 20)
    fp = sum(1 for r in rows if r["label"] == 0 and r[key] >= 20)
    tn = sum(1 for r in rows if r["label"] == 0 and r[key] < 20)
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
    acc = (tp + tn) / len(rows) if rows else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(p, 3), "recall": round(rc, 3),
            "f1": round(f1, 3), "akurasi": round(acc, 3)}


def gemini_with_retry(teks, tries=6):
    """Satu panggilan Gemini per lowongan; tunggu lalu ulangi bila kuota per menit paket gratis habis."""
    import time
    from app import gemini
    for attempt in range(tries):
        try:
            return gemini.analyze(teks)
        except gemini.AIUnavailable as exc:
            if attempt == tries - 1:
                raise
            wait = 20 * (attempt + 1)
            print(f"  AI belum bisa ({exc}); tunggu {wait} detik")
            time.sleep(wait)


def ai_only_score(data, teks):
    """Versi pembanding: rambu dari AI saja (tanpa aturan), tetap dengan bobot katalog."""
    from app.analyzer import _claim_matches, evidence_in_text
    from app.rambu import KATALOG
    kodes = {r.get("kode") for r in data.get("rambu", []) if r.get("kode") in KATALOG
             and evidence_in_text(str(r.get("bukti", "")), teks)
             and _claim_matches(r.get("kode"), str(r.get("bukti", "")))}
    return min(100, sum(KATALOG[k].bobot for k in kodes)), sorted(kodes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true")
    ap.add_argument("--set", choices=list(FILES), default="uji")
    ap.add_argument("--ulang", action="store_true",
                    help="hitung ulang memakai jawaban AI yang tersimpan (tanpa memanggil AI lagi)")
    args = ap.parse_args()
    if not args.ai:
        os.environ["RAMBU_AI"] = "off"
    from app import analyzer, config

    rows = load(args.set)
    if not rows:
        sys.exit(f"Data set '{args.set}' belum ada.")
    for r in rows:
        res = analyzer.analyze(r["teks"], use_ai=False)
        r["skor_aturan"] = res["skor"]
        r["rambu_aturan"] = [x["kode"] for x in res["rambu"]]
    report = {"set": args.set, "jumlah": len(rows), "penipuan": sum(r["label"] for r in rows),
              "asli": sum(1 - r["label"] for r in rows), "aturan": metrics(rows, "skor_aturan")}

    if args.ulang:
        old = {r["id"]: r for r in json.loads((ROOT / "docs" / f"hasil-evaluasi-{args.set}.json")
                                              .read_text(encoding="utf-8"))["per_item"]}
        for r in rows:
            data = old[r["id"]]["jawaban_ai"]
            r["jawaban_ai"] = data
            r["skor_ai"], r["rambu_ai"] = ai_only_score(data, r["teks"])
            res = analyzer.analyze(r["teks"], ai_data=data)
            r["skor_gabungan"] = res["skor"]
            r["rambu_gabungan"] = [x["kode"] for x in res["rambu"]]
            r["sumber"] = res["sumber"]["status"]
        report["ai_saja"] = metrics(rows, "skor_ai")
        report["aturan_ai"] = metrics(rows, "skor_gabungan")
    elif args.ai:
        if not config.ai_available():
            sys.exit("GEMINI_API_KEY belum diatur di .env")
        for i, r in enumerate(rows, 1):
            print(f"[{i}/{len(rows)}] {r['id']}")
            data = gemini_with_retry(r["teks"])
            r["jawaban_ai"] = data  # disimpan agar hasil bisa dihitung ulang tanpa memanggil AI lagi
            r["skor_ai"], r["rambu_ai"] = ai_only_score(data, r["teks"])
            res = analyzer.analyze(r["teks"], ai_data=data)
            r["skor_gabungan"] = res["skor"]
            r["rambu_gabungan"] = [x["kode"] for x in res["rambu"]]
            r["sumber"] = res["sumber"]["status"]
        report["ai_saja"] = metrics(rows, "skor_ai")
        report["aturan_ai"] = metrics(rows, "skor_gabungan")

    out = ROOT / "docs" / f"hasil-evaluasi-{args.set}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"ringkasan": report, "per_item": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Set {args.set}: {report['jumlah']} lowongan ({report['penipuan']} penipuan, {report['asli']} asli)")
    for key in ("aturan", "ai_saja", "aturan_ai"):
        if key in report:
            m = report[key]
            print(f"{key:<10} precision {m['precision']:.2f}  recall {m['recall']:.2f}  F1 {m['f1']:.2f}  "
                  f"akurasi {m['akurasi']:.2f}  (TP {m['tp']} FP {m['fp']} FN {m['fn']} TN {m['tn']})")
    print(f"Detail per item: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
