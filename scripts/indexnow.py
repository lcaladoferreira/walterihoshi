#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Submete as URLs canônicas do sitemap ao endpoint global do IndexNow."""
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
CONFIG = RAIZ / "data" / "config.json"
KEY = "202e4b3de199cff1c7f73a7f88dab545"
ENDPOINT = "https://api.indexnow.org/indexnow"


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    site = str(cfg["site_url"]).rstrip("/")
    host = site.split("//", 1)[1]

    key_file = PUBLIC / (KEY + ".txt")
    key_file.write_text(KEY + "\n", encoding="utf-8")

    raiz = ET.parse(PUBLIC / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [n.text.strip() for n in raiz.findall("sm:url/sm:loc", ns) if n.text]
    if not urls:
        raise RuntimeError("Nenhuma URL encontrada no sitemap")

    payload = json.dumps({
        "host": host,
        "key": KEY,
        "keyLocation": site + "/" + KEY + ".txt",
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 202):
            raise RuntimeError("IndexNow retornou HTTP %s" % resp.status)
    print("IndexNow: %d URLs submetidas." % len(urls))


if __name__ == "__main__":
    main()
