"""Membuka tautan lowongan secara aman untuk melihat tujuan aslinya.

Hanya mengikuti pengalihan (redirect) dan membaca kode status; isi halaman tidak dieksekusi atau disimpan.
Pengaman: hanya http/https di port standar, alamat IP privat/lokal ditolak (mencegah SSRF),
maksimal 4 lompatan, batas waktu pendek, dan maksimal 5 tautan per pemeriksaan.
"""

import ipaddress
import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from . import config

log = logging.getLogger("rambu.tautan")
MAX_LINKS = 5
MAX_HOPS = 4
TIMEOUT = 4.0
UA = "Mozilla/5.0 (compatible; Lamarin-LinkCheck/1.0; +https://lamarin-one.vercel.app)"


@dataclass
class Cek:
    url: str
    tujuan: str = ""        # URL akhir setelah pengalihan
    host_tujuan: str = ""
    status: int = 0         # kode HTTP akhir; 0 = tidak bisa dibuka
    lompatan: int = 0
    galat: str = ""


def _public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def _check(url: str) -> Cek:
    cur = url if url.startswith(("http://", "https://")) else "https://" + url
    res = Cek(url=url)
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": UA}) as client:
        for hop in range(MAX_HOPS + 1):
            parts = urlsplit(cur)
            host = (parts.hostname or "").lower()
            if parts.scheme not in ("http", "https") or (parts.port not in (None, 80, 443)) or not host:
                res.galat = "alamat tidak didukung"
                return res
            if not _public_host(host):
                res.galat = "domain tidak ditemukan"
                return res
            try:
                with client.stream("GET", cur) as resp:
                    res.status, res.tujuan, res.host_tujuan, res.lompatan = resp.status_code, cur, host, hop
                    loc = resp.headers.get("location")
            except httpx.HTTPError as exc:
                res.galat = "tidak bisa dibuka"
                log.info("cek tautan %s gagal: %s", cur, type(exc).__name__)
                return res
            if res.status in (301, 302, 303, 307, 308) and loc:
                cur = urljoin(cur, loc)
                continue
            return res
    res.galat = "terlalu banyak pengalihan"
    return res


def check_all(urls: list[str]) -> dict[str, Cek]:
    """Cek beberapa tautan sekaligus. Mengembalikan {} bila pengecekan daring dimatikan."""
    if not config.LINK_CHECK or not urls:
        return {}
    urls = list(dict.fromkeys(urls))[:MAX_LINKS]
    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        return dict(zip(urls, pool.map(_check, urls)))
