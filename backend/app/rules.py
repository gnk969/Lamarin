"""Pendeteksi rambu berbasis aturan (tanpa AI).

Setiap temuan menyertakan potongan teks sebagai bukti, supaya pengguna bisa melihat sendiri
bagian lowongan yang dimaksud. Aturan sengaja konservatif: kata yang lazim di lowongan asli
(mis. "fotokopi KTP" sebagai berkas lamaran) tidak otomatis dianggap rambu.
"""

import re
from dataclasses import dataclass

NEGATION = re.compile(r"(tidak|tanpa|tdk|bebas|gratis|tak|bukan|tidak ada|tidak dipungut)\W+(\w+\W+){0,3}$")

SHORTENERS = ("bit.ly", "s.id", "tinyurl.com", "cutt.ly", "shorturl.at", "rebrand.ly", "t.ly", "is.gd",
              "linktr.ee", "wa.link", "rb.gy", "ow.ly", "goo.gl", "lynk.id")
FREE_HOSTS = ("workers.dev", "pages.dev", "blogspot.", "wixsite.com", "weebly.com", "wordpress.com",
              "github.io", "web.app", "firebaseapp.com", "netlify.app", "vercel.app", "000webhostapp",
              "glitch.me", "ngrok", "sites.google.com", "forms.gle", "docs.google.com/forms",
              "form.jotform", "typeform.com", "my.id", "biz.id", "rf.gd", "epizy.com")
OFFICIAL_SUFFIXES = (".go.id", ".co.id", ".ac.id", ".or.id", ".mil.id", ".sch.id", ".desa.id")
OFFICIAL_PORTALS = ("fhcibumn.id", "kemnaker.go.id", "bkn.go.id")
GENERIC_TLDS = ("com", "net", "org", "info", "xyz", "site", "online", "top", "click", "live", "store", "shop",
                "biz", "cc", "cx", "icu", "vip", "work", "fun", "id")
FREE_EMAIL = ("gmail.com", "yahoo.com", "yahoo.co.id", "hotmail.com", "outlook.com", "ymail.com",
              "proton.me", "protonmail.com", "aol.com", "icloud.com")

URL_RE = re.compile(
    r"((?:https?://)?(?:[a-z0-9-]+(?:\.|\[dot\]|\(dot\)|\[\.\]))+[a-z]{2,}(?:/[^\s\"'<>)]*)?)", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", re.I)
PHONE_RE = re.compile(r"(?:\+?62|0)\s?8[\d\s\-.x]{7,14}[\dx]|wa\.me/\S+|t\.me/\S+", re.I)
MONEY_RE = re.compile(r"rp\.?\s?[\d.,]+\s?(?:jt|juta|rb|ribu|k)?|\b\d+(?:[.,]\d+)?\s?(?:jt|juta|rb|ribu)\b"
                      r"|\b\d{1,3}(?:[.,]\d{3})+(?=\s?idr\b)", re.I)


@dataclass
class Temuan:
    kode: str
    bukti: str
    sumber: str = "aturan"


_SENTENCE_END = re.compile(r"\n|[.!?](?=\s|$)")


def _snippet(text: str, start: int, end: int, pad: int = 120) -> str:
    """Potongan kalimat yang memuat temuan, dibatasi tanda akhir kalimat dan maksimal sekitar 2x pad."""
    a = max(0, start - pad)
    ends_before = [m.end() for m in _SENTENCE_END.finditer(text, a, start)]
    a = ends_before[-1] if ends_before else a
    nxt = _SENTENCE_END.search(text, end, min(len(text), end + pad))
    b = nxt.end() if nxt else min(len(text), end + pad)
    while a > 0 and a < start and text[a - 1].isalnum():
        a -= 1
    while b < len(text) and text[b - 1].isalnum() and text[b].isalnum():
        b += 1
    return " ".join(text[a:b].split())


def _negated(low: str, start: int) -> bool:
    """Negasi hanya dihitung di kalimat/baris yang sama ("tanpa pengalaman." tidak menegasi kalimat berikutnya)."""
    window = low[max(0, start - 40):start]
    window = re.split(r"[.!?\n,;:]", window)[-1]
    return bool(NEGATION.search(window))


def _first(pattern: str, text: str, low: str, check_negation: bool = False) -> str | None:
    for m in re.finditer(pattern, low, re.I | re.S):
        if check_negation and _negated(low, m.start()):
            continue
        return _snippet(text, m.start(), m.end())
    return None


def _deobfuscate(low: str) -> str:
    return re.sub(r"\s?(\[dot\]|\(dot\)|\[\.\])\s?", ".", low)


def _money_to_rupiah(token: str) -> float | None:
    t = token.lower().replace("rp", "").replace(" ", "")
    mult = 1.0
    for suffix, m in (("juta", 1e6), ("jt", 1e6), ("ribu", 1e3), ("rb", 1e3), ("k", 1e3)):
        if t.endswith(suffix):
            t, mult = t[: -len(suffix)], m
            break
    if mult == 1.0:
        t = t.replace(".", "").replace(",", "")
    else:
        t = t.replace(",", ".")
        if t.count(".") > 1:
            t = t.replace(".", "")
    try:
        return float(t) * mult
    except ValueError:
        return None


def domains_in(text: str) -> list[str]:
    low = _deobfuscate(text.lower())
    found = []
    for m in URL_RE.finditer(low):
        url = m.group(1)
        host = re.sub(r"^https?://", "", url).split("/")[0]
        tld = host.rsplit(".", 1)[-1]
        explicit = url.startswith(("http://", "https://", "www."))
        if "." in host and not host.replace(".", "").isdigit() and (explicit or tld in URL_TLDS):
            found.append(url)
    return found


# TLD yang dikenali sebagai tautan bila ditulis tanpa http:// (menghindari "transfer.kirim" dianggap tautan).
URL_TLDS = {"com", "id", "net", "org", "info", "xyz", "site", "online", "top", "click", "live", "store", "shop",
            "biz", "cc", "cx", "icu", "vip", "work", "fun", "ly", "gl", "me", "io", "app", "dev", "link", "gd",
            "at", "co", "us", "in", "my", "sg", "to", "tk", "ml", "ga", "cf", "gq", "pw", "ws", "tv", "uk", "au"}


def detect(text: str) -> list[Temuan]:
    low = text.lower()
    out: list[Temuan] = []

    def add(kode: str, bukti: str | None) -> None:
        if bukti and not any(t.kode == kode for t in out):
            out.append(Temuan(kode, bukti))

    # Biaya: kata biaya/bayar/transfer dekat konteks rekrutmen, atau nominal setelah kata pendaftaran dsb.
    add("MINTA_BIAYA", _first(
        r"\b(biaya|bayar(?:kan)?|membayar|transfer|tf|dp|uang|iuran|dana)\b[^.\n]{0,50}?"
        r"\b(pendaftaran|administrasi|admin|pelatihan|training|seragam|medical|mcu|tes kesehatan|"
        r"tiket|akomodasi|penginapan|jaminan|proses|visa|paspor|berkas|materai|registrasi|interview)\b",
        text, low, check_negation=True) or _first(
        r"\b(pendaftaran|administrasi|seragam|medical|pelatihan|registrasi|jaminan)\b[^.\n]{0,30}?"
        r"(rp\.?\s?\d|\b\d+\s?(rb|ribu|jt|juta)\b)", text, low, check_negation=True) or _first(
        # instruksi membayar ke rekening/e-wallet dengan nominal
        r"\b(pembayaran|selesaikan pembayaran|transfer ke|no\.?\s?rek|nomor rekening|e-?wallet|dana|ovo|gopay)\b"
        r"[\s\S]{0,160}?(rp\.?\s?\d)", text, low, check_negation=True) or _first(
        # biaya yang ditalangi lalu dipotong dari gaji
        r"\b(dana talang|potong gaji|dipotong dari gaji|menyetor|setor rp)\b", text, low))

    # Kerja online dengan misi/komisi/deposit
    deposit = _first(r"\b(deposit|top\s?up|isi saldo|setor dana|menyetor)\b", text, low)
    task = re.search(r"\b(like|follow|subscribe|rating|review|misi|tugas online|klik iklan)\b", low)
    reward = re.search(r"\b(komisi|cuan|bonus|reward|di ?bayar|bayaran|saldo|imbalan|freelance|"
                       r"pekerjaan sampingan|kerja sampingan|paruh waktu|part ?time)\b", low)
    if deposit:
        add("DEPOSIT_TUGAS", deposit)
    elif task and reward:
        add("DEPOSIT_TUGAS", _snippet(text, task.start(), task.end()))

    add("TRAVEL_WAJIB", _first(
        r"\b(wajib|harus|diwajibkan|mewajibkan|melalui|menggunakan jasa)\b[^.\n]{0,40}?"
        r"\b(travel|agen perjalanan|biro perjalanan|tour and travel)\b", text, low) or _first(
        # paket perjalanan (tiket + hotel) yang dijual perekrut
        r"\b(reservasi\w*|paket)\b[\s\S]{0,60}?\b(tiket|hotel|penginapan|penjemputan)\b", text, low))

    # Data sensitif: OTP/PIN selalu rambu; KTP/rekening hanya bila dikirim lewat chat/formulir tak resmi.
    sensitif = _first(r"\b(otp|kode verifikasi|kode otp|pin atm|pin m-?banking|password)\b", text, low) or _first(
        r"\bfoto\b[^.\n]{0,60}?\b(pakaian dalam|bra|underwear|tanpa busana|telanjang)\b", text, low)
    if not sensitif:
        doc = re.search(r"\b(ktp|nik|kartu keluarga|nomor rekening|no\.?\s?rek(?:ening)?|rekening bank|foto selfie)\b", low)
        channel = re.search(r"\b(whatsapp|wa|telegram|formulir|form|link|tautan|dm|inbox)\b", low)
        if doc and channel and abs(doc.start() - channel.start()) < 160:
            sensitif = _snippet(text, doc.start(), doc.end())
    add("MINTA_DATA_SENSITIF", sensitif)

    for url in domains_in(text):
        host = re.sub(r"^https?://", "", url).split("/")[0]
        official = host.endswith(OFFICIAL_SUFFIXES) or host.endswith(OFFICIAL_PORTALS)
        job_word_domain = (re.search(r"lowongan|loker|rekrutmen|recruitment|pendaftaran|daftar|karir|career|kerja", host)
                           and host.rsplit(".", 1)[-1] in GENERIC_TLDS and not official)
        if (any(s in url for s in SHORTENERS + FREE_HOSTS) or "bitly" in host
                or (re.search(r"[a-z]\d{2,}[a-z]|\d{3,}", host) and not official) or job_word_domain):
            add("TAUTAN_MENCURIGAKAN", url)
            break

    phone = next((m for m in PHONE_RE.finditer(low)
                  if m.group().startswith(("wa.me", "t.me")) or sum(c.isdigit() or c == "x" for c in m.group()) >= 10),
                 None)
    wa_word = re.search(r"\b(hubungi|chat|kirim|lamar|lamaran|daftar|pendaftaran|hub|info|via|melalui|ke|cek di|masuk)\b"
                        r"[^.\n]{0,25}\b(wa|whatsapp|telegram|tele|dm|direct message|inbox)\b", low)
    if phone:
        add("KONTAK_PRIBADI", _snippet(text, phone.start(), phone.end(), pad=25))
    elif wa_word:
        add("KONTAK_PRIBADI", _snippet(text, wa_word.start(), wa_word.end()))

    for m in EMAIL_RE.finditer(low):
        if m.group(1) in FREE_EMAIL:
            add("EMAIL_GRATISAN", _snippet(text, m.start(), m.end(), pad=0))
            break

    # Gaji tidak wajar (Rupiah): >= Rp15 juta/bulan, >= Rp3 juta/minggu, >= Rp300 ribu/hari, atau "puluhan juta".
    gaji_hit = _first(r"\b(gaji|penghasilan|pendapatan)\b[^.\n]{0,30}?\bpuluhan juta\b", text, low)
    if gaji_hit:
        add("GAJI_TIDAK_WAJAR", gaji_hit)
    for m in re.finditer(r"\b(gaji|penghasilan|pendapatan|upah|komisi|income|dibayar)\b[^\n]{0,60}", low):
        window = low[m.start(): m.end() + 30]
        amounts = [_money_to_rupiah(t.group()) for t in MONEY_RE.finditer(window)]
        amounts = [a for a in amounts if a]
        if not amounts:
            continue
        per_day = re.search(r"(/|per|setiap|se)\s?(hari|harian|jam)", window)
        per_week = re.search(r"(/|per|setiap|se)\s?(minggu|pekan)", window)
        if ((per_day and max(amounts) >= 300_000) or (per_week and max(amounts) >= 3_000_000)
                or max(amounts) >= 15_000_000):
            add("GAJI_TIDAK_WAJAR", _snippet(text, m.start(), min(len(text), m.end())))
            break

    add("SYARAT_TERLALU_MUDAH", _first(
        r"\b(tanpa pengalaman|tanpa perlu pengalaman|tanpa tes|tanpa interview|tanpa wawancara|tanpa ijazah|"
        r"tanpa minimal pendidikan|tidak perlu pengalaman|tidak ada pengalaman kerja tidak masalah|"
        r"tidak perlu ijazah|semua lulusan|usia bebas|langsung kerja|langsung diterima|pasti diterima|"
        r"tanpa modal)\b", text, low))

    add("DESAKAN_WAKTU", _first(
        r"\b(kuota terbatas|slot terbatas|tempat terbatas|segera daftar|daftar sekarang juga|hari ini juga|"
        r"buruan|jangan sampai ketinggalan|ditutup hari ini|terakhir hari ini|batas waktu pembayaran|"
        r"batas pembayaran)\b", text, low))

    overseas = re.search(
        r"\b(luar negeri|kapal pesiar|cruise ?ship|abk|jepang|korea|taiwan|hong ?kong|malaysia|singapura|"
        r"singapore|dubai|eropa|australia|selandia baru|new zealand|polandia|turki|kamboja|myanmar|magang)\b", low)
    licence = re.search(r"\b(p3mi|sip2mi|sip3mi|bp2mi|kp2mi|bp3mi|siskop2mi|p2mi|izin penempatan)\b", low)
    if overseas and not licence:
        add("LUAR_NEGERI_TANPA_IZIN", _snippet(text, overseas.start(), overseas.end()))

    return out
