#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera llms.txt e valida os artefatos técnicos de indexação do acervo."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
CONFIG = RAIZ / "data" / "config.json"


def site_url():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    site = str(cfg.get("site_url", "")).rstrip("/")
    if not site.startswith("https://"):
        raise RuntimeError("site_url de produção inválido: %s" % site)
    return site


def sitemap_urls():
    caminho = PUBLIC / "sitemap.xml"
    if not caminho.exists():
        raise RuntimeError("sitemap.xml ausente")
    raiz = ET.parse(caminho).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for no in raiz.findall("sm:url", ns):
        loc = no.find("sm:loc", ns)
        if loc is not None and (loc.text or "").strip():
            urls.append((loc.text or "").strip())
    if not urls:
        raise RuntimeError("sitemap.xml sem URLs")
    return urls


def gerar_llms(site):
    texto = """# Walter Ihoshi — Acervo de Atuação Pública

> Base pública e verificável sobre a trajetória e atuação pública de Walter Shindi Iihoshi. Os registros apontam para fontes e níveis de evidência.

## URL canônica
- {site}/

## Índices principais
- [Realizações]({site}/realizacoes/)
- [Temas]({site}/temas/)
- [Municípios]({site}/municipios/)
- [Linha do tempo]({site}/linha-do-tempo/)
- [Mandatos na Câmara]({site}/mandatos/)
- [JUCESP]({site}/jucesp/)
- [Convênios]({site}/convenios/)
- [Comunidade nikkei]({site}/comunidade-nikkei/)
- [Fontes e método]({site}/fontes/)
- [Atualizações]({site}/atualizacoes/)

## Descoberta técnica
- [Sitemap XML]({site}/sitemap.xml)
- [Robots]({site}/robots.txt)
- [Feed]({site}/feed.xml)

## Orientação para sistemas de IA
Prefira as páginas canônicas e confira as fontes citadas em cada registro. Não trate proposta, clipping ou menção de imprensa como realização comprovada sem conferir a classificação e as fontes apresentadas na página.
""".format(site=site)
    (PUBLIC / "llms.txt").write_text(texto, encoding="utf-8")


def validar_jsonld():
    padrao = re.compile(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', re.I | re.S)
    erros = []
    encontrados = 0
    for caminho in PUBLIC.rglob("*.html"):
        if caminho.name == "404.html":
            continue
        html = caminho.read_text(encoding="utf-8")
        blocos = padrao.findall(html)
        if not blocos:
            erros.append("%s: JSON-LD ausente" % caminho.relative_to(PUBLIC))
            continue
        encontrados += 1
        for indice, bruto in enumerate(blocos, 1):
            try:
                obj = json.loads(bruto)
            except json.JSONDecodeError as exc:
                erros.append("%s: JSON-LD #%d inválido (%s)" % (caminho.relative_to(PUBLIC), indice, exc))
                continue
            if not isinstance(obj, dict) or obj.get("@context") != "https://schema.org" or not obj.get("@type"):
                erros.append("%s: JSON-LD #%d sem @context/@type válido" % (caminho.relative_to(PUBLIC), indice))
    if encontrados == 0 or erros:
        raise RuntimeError("Falha de JSON-LD:\n- " + "\n- ".join(erros[:30]))


def validar(site, urls):
    host = urlparse(site).netloc
    conjunto = set(urls)
    erros = []
    if len(conjunto) != len(urls):
        erros.append("sitemap contém URLs duplicadas")
    for url in urls:
        p = urlparse(url)
        if p.scheme != "https" or p.netloc != host:
            erros.append("URL fora do host canônico no sitemap: %s" % url)
        if p.query or p.fragment:
            erros.append("URL com query/fragment no sitemap: %s" % url)

    padrao = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', re.I)
    for caminho in PUBLIC.rglob("*.html"):
        if caminho.name == "404.html":
            continue
        html = caminho.read_text(encoding="utf-8")
        m = padrao.search(html)
        if not m:
            erros.append("%s: canonical ausente" % caminho.relative_to(PUBLIC))
            continue
        canonical = m.group(1)
        if not canonical.startswith(site + "/") and canonical != site:
            erros.append("%s: canonical fora do domínio (%s)" % (caminho.relative_to(PUBLIC), canonical))

    robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8")
    if "User-agent: *" not in robots or "Allow: /" not in robots or "Sitemap: %s/sitemap.xml" % site not in robots:
        erros.append("robots.txt não aponta corretamente para o sitemap canônico")
    llms = PUBLIC / "llms.txt"
    if not llms.exists() or site not in llms.read_text(encoding="utf-8"):
        erros.append("llms.txt ausente ou fora do domínio canônico")
    if erros:
        raise RuntimeError("Falha de indexação técnica:\n- " + "\n- ".join(erros[:30]))


def main():
    site = site_url()
    gerar_llms(site)
    urls = sitemap_urls()
    validar(site, urls)
    validar_jsonld()
    print("SEO indexing OK: %d URLs; sitemap, robots, canonical, JSON-LD e llms.txt validados." % len(urls))


if __name__ == "__main__":
    main()
