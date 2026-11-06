"""Verifikasi sumber: apakah saluran pendaftaran cocok dengan instansi/perusahaan yang disebut lowongan.

Pemeriksaan ini dijalankan kode (bukan AI), jadi hasilnya pasti dan bisa diaudit:
- Domain .go.id, .ac.id, .sch.id, .mil.id, .desa.id hanya bisa didaftarkan instansi resmi dengan dokumen,
  jadi penipu tidak bisa membuat tautan pendaftaran di domain itu.
- Untuk perusahaan/BUMN terkenal, domain resminya dicatat di KNOWN_ORGS.

Hasilnya:
- "resmi"       : pendaftaran hanya lewat domain resmi; rambu kontekstual (mis. mencatut instansi) tidak dipakai.
- "tidak_cocok" : menyebut instansi/perusahaan besar, tetapi pendaftaran lewat saluran tidak resmi.
- "campuran"    : ada domain resmi sekaligus saluran tidak resmi.
- "tidak_ada"   : tidak ada tautan atau email yang bisa dicek.
- "netral"      : ada tautan/email biasa yang tidak bisa dipastikan.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from . import rules

# Domain yang hanya bisa dimiliki instansi pemerintah/pendidikan resmi di Indonesia.
RESTRICTED_SUFFIXES = (".go.id", ".ac.id", ".sch.id", ".mil.id", ".desa.id")
# Portal lowongan resmi/tepercaya: bukan bukti identitas perusahaan, tetapi bukan saluran mencurigakan.
TRUSTED_PORTALS = ("fhcibumn.id", "jobstreet.co.id", "jobstreet.com", "linkedin.com", "glints.com",
                   "kalibrr.com", "id.indeed.com", "indeed.com", "karirhub.kemnaker.go.id", "instagram.com")


@dataclass(frozen=True)
class Org:
    nama: str
    pola: str            # regex nama di teks (huruf kecil)
    domain: tuple        # domain resmi; kosong = instansi pemerintah (harus .go.id)
    situs: str           # alamat yang disarankan untuk dicek pengguna
    akun: tuple = ()     # akun media sosial resmi yang sudah dipastikan (tanpa @)


KNOWN_ORGS = [
    Org("Kementerian Kesehatan", r"kementerian kesehatan|kemenkes|kemkes", ("kemkes.go.id",), "https://www.kemkes.go.id",
        ("kemenkes_ri",)),
    Org("Kementerian Ketenagakerjaan", r"kementerian ketenagakerjaan|kemnaker", ("kemnaker.go.id",), "https://karirhub.kemnaker.go.id"),
    Org("BKN / CASN", r"\bbkn\b|badan kepegawaian|\bcpns\b|\bpppk\b|\bcasn\b", ("bkn.go.id",), "https://sscasn.bkn.go.id"),
    Org("BP2MI / KP2MI", r"bp2mi|kp2mi|bp3mi|pelindungan pekerja migran", ("bp2mi.go.id", "kp2mi.go.id"), "https://bp2mi.go.id"),
    Org("Rekrutmen Bersama BUMN", r"rekrutmen bersama bumn|\brbb\b|fhci", ("fhcibumn.id",), "https://rekrutmenbersama.fhcibumn.id"),
    Org("PLN", r"\bpln\b|perusahaan listrik negara", ("pln.co.id",), "https://web.pln.co.id/karier"),
    Org("Pertamina", r"pertamina", ("pertamina.com",), "https://recruitment.pertamina.com"),
    Org("Telkom Indonesia", r"\btelkom\b(?! ?sel)", ("telkom.co.id",), "https://www.telkom.co.id"),
    Org("Telkomsel", r"telkomsel", ("telkomsel.com",), "https://www.telkomsel.com"),
    Org("Bank Rakyat Indonesia", r"\bbri\b|bank rakyat indonesia", ("bri.co.id",), "https://bri.co.id/karir"),
    Org("Bank Negara Indonesia", r"\bbni\b|bank negara indonesia", ("bni.co.id",), "https://www.bni.co.id"),
    Org("Bank Mandiri", r"bank mandiri|\blivin\b", ("bankmandiri.co.id",), "https://www.bankmandiri.co.id"),
    Org("Bank Syariah Indonesia", r"\bbsi\b|bank syariah indonesia", ("bankbsi.co.id",), "https://www.bankbsi.co.id"),
    Org("BTN", r"\bbtn\b|bank tabungan negara", ("btn.co.id",), "https://www.btn.co.id"),
    Org("BCA", r"\bbca\b|bank central asia", ("bca.co.id",), "https://karir.bca.co.id"),
    Org("KAI", r"\bpt kai\b|kereta api indonesia", ("kai.id",), "https://recruitment.kai.id"),
    Org("Garuda Indonesia", r"garuda indonesia", ("garuda-indonesia.com",), "https://www.garuda-indonesia.com"),
    Org("Pelindo", r"pelindo", ("pelindo.co.id",), "https://www.pelindo.co.id"),
    Org("InJourney / Angkasa Pura", r"injourney|angkasa pura", ("injourney.id", "injourneyairports.id", "ap1.co.id"), "https://injourney.id"),
    Org("Pos Indonesia", r"pos indonesia", ("posindonesia.co.id", "pos.co.id"), "https://www.posindonesia.co.id"),
    Org("Indomaret", r"indomaret", ("indomaret.co.id",), "https://indomaret.co.id"),
    Org("Alfamart", r"alfamart", ("alfamart.co.id",), "https://alfamart.co.id"),
    Org("Astra", r"astra international|\bpt astra\b", ("astra.co.id",), "https://www.astra.co.id"),
    Org("Royal Caribbean", r"royal caribbean", ("rclcareers.com", "royalcaribbean.com", "rclcorporate.com"), "https://www.rclcareers.com"),
    Org("Carnival", r"carnival (cruise|corporation|corp)", ("carnival.com", "carnivalcorp.com"), "https://www.carnivalcorp.com"),
    Org("MSC Cruises", r"msc cruises", ("msccruises.com", "msc.com"), "https://www.msccruises.com"),
    Org("Marriott", r"marriott", ("marriott.com",), "https://careers.marriott.com"),
    Org("Accor", r"accor|novotel|movenpick|mövenpick|pullman|sofitel|ibis", ("accor.com",), "https://careers.accor.com"),
]
# Klaim instansi pemerintah umum: saluran resmi harus berdomain pemerintah/pendidikan.
GOV_CLAIM = re.compile(
    r"\b(kementerian|kemenkes|kemnaker|kemendikbud\w*|kemendikdasmen|kemenag|kemensos|kemenhub|kemenkeu|kemendagri|"
    r"kemenpar\w*|kemenpan\w*|kemenkumham|kementan|kemenperin|kemendag|kemenlu|kemenhan|komdigi|badan nasional|"
    r"pemerintah (kota|kabupaten|provinsi)|pemkab|pemkot|pemprov|rsud|puskesmas|kepolisian|polri|instansi pemerintah|"
    r"dinas (kesehatan|pendidikan|tenaga kerja|ketenagakerjaan|sosial|perhubungan|pariwisata|kependudukan))\b")


# Layanan yang bisa dipakai siapa saja secara gratis: bukan milik instansi/perusahaan mana pun.
LINK_SERVICES = {
    "msha.ke": "Milkshake (pembuat halaman link-in-bio gratis)", "milkshake.app": "Milkshake (link-in-bio gratis)",
    "linktr.ee": "Linktree (link-in-bio gratis)", "lynk.id": "Lynk (link-in-bio gratis)", "bio.link": "bio.link (link-in-bio gratis)",
    "heylink.me": "HeyLink (link-in-bio gratis)", "beacons.ai": "Beacons (link-in-bio gratis)", "taplink.cc": "Taplink (link-in-bio gratis)",
    "carrd.co": "Carrd (pembuat situs gratis)", "bit.ly": "Bitly (pemendek tautan)", "s.id": "S.id (pemendek tautan)",
    "tinyurl.com": "TinyURL (pemendek tautan)", "cutt.ly": "Cuttly (pemendek tautan)", "shorturl.at": "ShortURL (pemendek tautan)",
    "rb.gy": "Rebrandly (pemendek tautan)", "t.ly": "T.ly (pemendek tautan)", "wa.link": "wa.link (pemendek tautan WhatsApp)",
    "forms.gle": "Google Form (formulir gratis)", "docs.google.com": "Google Docs/Form (gratis)", "sites.google.com": "Google Sites (situs gratis)",
    "blogspot.com": "Blogspot (blog gratis)", "wordpress.com": "WordPress.com (blog gratis)", "wixsite.com": "Wix (situs gratis)",
    "weebly.com": "Weebly (situs gratis)", "vercel.app": "Vercel (hosting gratis)", "netlify.app": "Netlify (hosting gratis)",
    "github.io": "GitHub Pages (hosting gratis)", "web.app": "Firebase (hosting gratis)", "jotform.com": "Jotform (formulir gratis)",
    "typeform.com": "Typeform (formulir gratis)", "wa.me": "Tautan chat WhatsApp", "t.me": "Tautan chat Telegram",
}
SOCIAL = {"instagram.com": "Instagram", "tiktok.com": "TikTok", "facebook.com": "Facebook", "fb.com": "Facebook",
          "x.com": "X/Twitter", "twitter.com": "X/Twitter", "youtube.com": "YouTube", "linkedin.com": "LinkedIn"}
# @nama yang bukan bagian dari alamat email
HANDLE_RE = re.compile(r"(?<![\w.@])@([a-z0-9_][a-z0-9_.]{1,28}[a-z0-9_])\b(?!@)", re.I)


@dataclass
class Hasil:
    status: str
    pesan: str
    instansi: str = ""
    domain_resmi: list = field(default_factory=list)
    saluran_tidak_resmi: list = field(default_factory=list)
    cek_manual: list = field(default_factory=list)
    item: list = field(default_factory=list)   # pemeriksaan satu per satu: tautan, email, nomor, akun


def _host(url: str) -> str:
    return re.sub(r"^https?://", "", url.lower()).split("/")[0].split(":")[0].removeprefix("www.")


def _ends(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _service(host: str) -> str:
    return next((name for d, name in LINK_SERVICES.items() if _ends(host, d)), "")


def _claimed_org(low: str, perusahaan: str) -> Org | None:
    hay = f"{low} {perusahaan.lower()}"
    for org in KNOWN_ORGS:
        if re.search(org.pola, hay):
            return org
    return None


def _short(values: list) -> list:
    return [_host(v) if ("/" in v or v.startswith("http")) else v for v in values]


def verify(text: str, perusahaan: str = "", has_personal_contact: bool = False,
           cek: dict | None = None) -> Hasil:
    low = text.lower()
    cek = cek or {}
    org = _claimed_org(low, perusahaan)
    gov_claim = bool(GOV_CLAIM.search(low)) or (org is not None and any(d.endswith(RESTRICTED_SUFFIXES) for d in org.domain))
    nama = org.nama if org else ("instansi pemerintah" if gov_claim else "")
    claimed = bool(org or gov_claim)
    harap = ", ".join(org.domain) if org else "domain .go.id"

    def official(h: str) -> bool:
        return h.endswith(RESTRICTED_SUFFIXES) or bool(org and any(_ends(h, d) for d in org.domain))

    items, resmi, tidak_resmi = [], [], []

    def add(jenis, nilai, status, alasan):
        items.append({"jenis": jenis, "nilai": nilai, "status": status, "alasan": alasan})
        if status == "resmi":
            resmi.append(nilai)
        elif status == "bahaya" or (status == "waspada" and claimed and jenis != "akun"):
            tidak_resmi.append(nilai)

    def akun(platform: str, handle: str) -> None:
        h = handle.lower().lstrip("@")
        if not h or any(i["nilai"] == f"@{h}" for i in items):
            return
        if org and h in org.akun:
            add("akun", f"@{h}", "resmi", f"Akun {platform} resmi {org.nama} yang tercatat.")
        elif org and org.akun:
            add("akun", f"@{h}", "waspada", f"Bukan akun resmi {org.nama} yang tercatat (@{', @'.join(org.akun)}). "
                "Akun tiruan sering memakai nama yang mirip.")
        else:
            add("akun", f"@{h}", "info", f"Akun {platform}. Pastikan bercentang biru dan tercantum di situs resmi.")

    # 1) Tautan
    for url in rules.domains_in(text):
        host = _host(url)
        c = cek.get(url)
        broken = bool(c and (c.galat or c.status >= 400))
        final = c.host_tujuan.removeprefix("www.") if c and c.host_tujuan else ""
        online = ""
        if c:
            if c.galat:
                online = f" Saat dibuka: {c.galat}."
            elif c.status >= 400:
                online = f" Saat dibuka: halaman tidak ditemukan (kode {c.status})."
            elif final and final != host:
                online = f" Saat dibuka, tautan ini mengarah ke {final}."
        social = next((n for d, n in SOCIAL.items() if _ends(host, d)), "")
        if social:
            path = re.sub(r"^https?://", "", url).split("/", 1)
            akun(social, path[1].split("/")[0].split("?")[0] if len(path) > 1 else "")
            continue
        svc = _service(host)
        if official(host):
            add("tautan", url, "waspada" if broken else "resmi",
                f"Domain resmi {nama or 'pemerintah/pendidikan'} ({host}); domain ini tidak bisa dibuat oleh penipu.{online}")
        elif svc and final and official(final) and not broken:
            add("tautan", url, "resmi", f"{svc}, tetapi tujuan aslinya domain resmi {final}.{online}")
        elif svc:
            why = (f"{svc}. Siapa saja bisa membuatnya, jadi bukan bukti milik {nama}; domain resminya {harap}."
                   if claimed else f"{svc}. Siapa saja bisa membuatnya; pastikan tujuan akhirnya situs resmi perusahaan.")
            add("tautan", url, "bahaya" if claimed else "waspada", why + online)
        elif any(_ends(host, p) for p in TRUSTED_PORTALS):
            add("tautan", url, "info", f"Portal lowongan terkenal ({host}). Pastikan akun perusahaannya terverifikasi.{online}")
        elif claimed:
            add("tautan", url, "bahaya", f"Domain {host} bukan milik {nama}; domain resminya {harap}.{online}")
        else:
            add("tautan", url, "waspada" if broken else "info",
                f"Domain {host} tidak dikenal. Cocokkan dengan situs resmi perusahaan sebelum mengisi data.{online}")

    # 2) Email
    for m in rules.EMAIL_RE.finditer(low):
        addr, dom = m.group(0), m.group(1).lower()
        if official(dom):
            add("email", addr, "resmi", f"Email berdomain resmi ({dom}).")
        elif dom in rules.FREE_EMAIL:
            add("email", addr, "bahaya" if claimed else "waspada",
                f"Email gratis ({dom}) bisa dibuat siapa saja." + (f" {nama} memakai email {harap}." if claimed else ""))
        elif claimed:
            add("email", addr, "bahaya", f"Domain email {dom} bukan milik {nama} ({harap}).")
        else:
            add("email", addr, "info", f"Email perusahaan ({dom}); cocokkan dengan situs resmi.")

    # 3) Nomor telepon / WhatsApp
    if has_personal_contact:
        num = next((m.group().strip() for m in rules.PHONE_RE.finditer(low)), "chat WhatsApp/DM")
        add("nomor", num, "bahaya" if claimed else "waspada",
            "Nomor atau chat pribadi. Rekrutmen resmi memakai portal atau email resmi, bukan nomor perorangan.")

    # 4) Akun media sosial yang ditulis sebagai @nama
    for m in HANDLE_RE.finditer(text):
        akun("media sosial", m.group(1))

    resmi, tidak_resmi = list(dict.fromkeys(resmi)), list(dict.fromkeys(tidak_resmi))
    cek_manual = []
    if org:
        cek_manual.append({"label": f"Situs resmi {org.nama}", "url": org.situs})
    if nama:
        q = quote_plus(f"{org.nama if org else 'lowongan instansi'} lowongan hoaks site:turnbackhoax.id")
        cek_manual.append({"label": "Cari laporan hoaks terkait", "url": f"https://www.google.com/search?q={q}"})

    resmi_ch = [v for v in resmi if not v.startswith("@")]   # akun sosmed saja bukan saluran pendaftaran
    has_channel = any(i["jenis"] in ("tautan", "email") for i in items)
    if resmi_ch and not tidak_resmi:
        return Hasil("resmi", f"Pendaftaran diarahkan ke saluran resmi ({', '.join(_short(resmi_ch))}). Domain ini hanya "
                     "bisa dimiliki instansi atau perusahaan tersebut, sehingga tidak bisa dipalsukan penipu.",
                     nama, resmi, [], cek_manual, items)
    if resmi_ch and tidak_resmi:
        return Hasil("campuran", f"Ada saluran resmi ({', '.join(_short(resmi_ch))}), tetapi juga saluran tidak resmi "
                     f"({', '.join(_short(tidak_resmi))}). Daftar hanya lewat saluran resmi.",
                     nama, resmi, tidak_resmi, cek_manual, items)
    if claimed and tidak_resmi:
        return Hasil("tidak_cocok", f"Lowongan mengatasnamakan {nama}, tetapi pendaftarannya lewat "
                     f"{', '.join(_short(tidak_resmi))}, bukan {harap}.", nama, [], tidak_resmi, cek_manual, items)
    if not has_channel:
        return Hasil("tidak_ada", "Tidak ada tautan atau email pendaftaran yang bisa dicek. "
                     "Pastikan lowongan ini juga diumumkan di situs atau akun resmi.", nama, [], tidak_resmi, cek_manual, items)
    return Hasil("netral", "Tautan atau email di lowongan bukan domain resmi yang dikenal. Cocokkan dengan "
                 "situs resmi perusahaan sebelum melamar.", nama, [], tidak_resmi, cek_manual, items)
