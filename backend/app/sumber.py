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


KNOWN_ORGS = [
    Org("Kementerian Kesehatan", r"kementerian kesehatan|kemenkes|kemkes", ("kemkes.go.id",), "https://www.kemkes.go.id"),
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


@dataclass
class Hasil:
    status: str
    pesan: str
    instansi: str = ""
    domain_resmi: list = field(default_factory=list)
    saluran_tidak_resmi: list = field(default_factory=list)
    cek_manual: list = field(default_factory=list)


def _host(url: str) -> str:
    return re.sub(r"^https?://", "", url.lower()).split("/")[0].removeprefix("www.")


def _ends(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _claimed_org(low: str, perusahaan: str) -> Org | None:
    hay = f"{low} {perusahaan.lower()}"
    for org in KNOWN_ORGS:
        if re.search(org.pola, hay):
            return org
    return None


def verify(text: str, perusahaan: str = "", has_personal_contact: bool = False) -> Hasil:
    low = text.lower()
    org = _claimed_org(low, perusahaan)
    gov_claim = bool(GOV_CLAIM.search(low)) or (org is not None and any(d.endswith(RESTRICTED_SUFFIXES) for d in org.domain))

    hosts = [_host(u) for u in rules.domains_in(text)]
    emails = [m.group(1).lower() for m in rules.EMAIL_RE.finditer(low)]

    def official(h: str) -> bool:
        return h.endswith(RESTRICTED_SUFFIXES) or bool(org and any(_ends(h, d) for d in org.domain))

    resmi = sorted({h for h in hosts + emails if official(h)})
    tidak_resmi = []
    for h in hosts:
        if official(h) or any(_ends(h, p) for p in TRUSTED_PORTALS):
            continue
        if any(_ends(h, s) for s in rules.SHORTENERS) or any(s in h for s in rules.FREE_HOSTS) or "bitly" in h:
            tidak_resmi.append(h)
        elif org or gov_claim:
            tidak_resmi.append(h)  # mengaku instansi/perusahaan tertentu tetapi memakai domain lain
    tidak_resmi += [e for e in emails if e in rules.FREE_EMAIL]
    if has_personal_contact:
        tidak_resmi.append("nomor WhatsApp/telepon pribadi")
    tidak_resmi = list(dict.fromkeys(tidak_resmi))

    nama = org.nama if org else ("instansi pemerintah" if gov_claim else "")
    cek = []
    if org:
        cek.append({"label": f"Situs resmi {org.nama}", "url": org.situs})
    if nama:
        q = quote_plus(f"{org.nama if org else 'lowongan instansi'} lowongan hoaks site:turnbackhoax.id")
        cek.append({"label": "Cari laporan hoaks terkait", "url": f"https://www.google.com/search?q={q}"})

    if resmi and not tidak_resmi:
        return Hasil("resmi", f"Pendaftaran diarahkan ke domain resmi ({', '.join(resmi)}). Domain ini hanya bisa "
                     "dimiliki instansi atau perusahaan tersebut, sehingga tidak bisa dipalsukan penipu.",
                     nama, resmi, [], cek)
    if resmi and tidak_resmi:
        return Hasil("campuran", f"Ada domain resmi ({', '.join(resmi)}), tetapi juga saluran tidak resmi "
                     f"({', '.join(tidak_resmi)}). Daftar hanya lewat domain resmi.", nama, resmi, tidak_resmi, cek)
    if (org or gov_claim) and tidak_resmi:
        harap = ", ".join(org.domain) if org else "domain .go.id"
        return Hasil("tidak_cocok", f"Lowongan mengatasnamakan {nama}, tetapi pendaftarannya lewat "
                     f"{', '.join(tidak_resmi)}, bukan {harap}.", nama, [], tidak_resmi, cek)
    if not hosts and not emails:
        return Hasil("tidak_ada", "Tidak ada tautan atau email pendaftaran yang bisa dicek. "
                     "Pastikan lowongan ini juga diumumkan di situs atau akun resmi.", nama, [], tidak_resmi, cek)
    return Hasil("netral", "Tautan atau email di lowongan bukan domain resmi yang dikenal. Cocokkan dengan "
                 "situs resmi perusahaan sebelum melamar.", nama, [], tidak_resmi, cek)
