#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pós-processamento SEO P0 para o build de produção no Vercel.

Mantém o gerador principal independente da hospedagem e aplica somente as
regras de indexação/canonical necessárias ao domínio de produção.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
SITE = "https://walterihoshi.vercel.app"

# Rotas úteis para navegação interna, mas que não devem disputar SERP nem
# consumir atenção do sitemap principal nesta fase.
EXCLUIR_SITEMAP = {
    f"{SITE}/busca/",
    f"{SITE}/temas/seguranca/",
    f"{SITE}/temas/educacao/",
}


def ajustar_busca_noindex():
    caminho = PUBLIC / "busca" / "index.html"
    if not caminho.exists():
        raise RuntimeError("Página /busca/ não foi gerada")

    html = caminho.read_text(encoding="utf-8")
    antigo = '<meta name="robots" content="index, follow">'
    novo = '<meta name="robots" content="noindex, follow">'
    if antigo not in html and novo not in html:
        raise RuntimeError("Meta robots esperado não encontrado em /busca/")
    if antigo in html:
        html = html.replace(antigo, novo, 1)
        caminho.write_text(html, encoding="utf-8")


def ajustar_sitemap():
    caminho = PUBLIC / "sitemap.xml"
    if not caminho.exists():
        raise RuntimeError("sitemap.xml não foi gerado")

    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    arvore = ET.parse(caminho)
    raiz = arvore.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    removidas = []
    for url in list(raiz.findall("sm:url", ns)):
        loc = url.find("sm:loc", ns)
        if loc is None or not (loc.text or "").startswith(SITE):
            raise RuntimeError(f"URL inválida no sitemap: {(loc.text if loc is not None else 'sem <loc>')}")

        # O build roda diariamente; usar a data do build como lastmod em todas
        # as URLs simularia alteração de conteúdo que não ocorreu. Até termos
        # lastmod por registro, é melhor omitir esse sinal do que enviá-lo falso.
        lastmod = url.find("sm:lastmod", ns)
        if lastmod is not None:
            url.remove(lastmod)

        if loc.text in EXCLUIR_SITEMAP:
            removidas.append(loc.text)
            raiz.remove(url)

    faltantes = EXCLUIR_SITEMAP - set(removidas)
    if faltantes:
        raise RuntimeError("Rotas esperadas não encontradas no sitemap: " + ", ".join(sorted(faltantes)))

    arvore.write(caminho, encoding="utf-8", xml_declaration=True)


def validar_canonicals():
    erros = []
    padrao = re.compile(r'<link rel="canonical" href="([^"]+)">')
    for caminho in PUBLIC.rglob("*.html"):
        html = caminho.read_text(encoding="utf-8")
        m = padrao.search(html)
        if not m:
            erros.append(f"{caminho.relative_to(PUBLIC)}: canonical ausente")
            continue
        canonical = m.group(1)
        if not canonical.startswith(SITE):
            erros.append(f"{caminho.relative_to(PUBLIC)}: canonical fora do domínio ({canonical})")
        if "lcaladoferreira.github.io" in canonical:
            erros.append(f"{caminho.relative_to(PUBLIC)}: canonical ainda aponta para GitHub Pages")

    if erros:
        raise RuntimeError("Falha de canonical:\n- " + "\n- ".join(erros[:20]))


def validar_robots():
    caminho = PUBLIC / "robots.txt"
    if not caminho.exists():
        raise RuntimeError("robots.txt não foi gerado")
    texto = caminho.read_text(encoding="utf-8")
    esperado = f"Sitemap: {SITE}/sitemap.xml"
    if "User-agent: *" not in texto or "Allow: /" not in texto or esperado not in texto:
        raise RuntimeError("robots.txt não aponta corretamente para o sitemap de produção")


def validar_resultado():
    sitemap = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8")
    if "<lastmod>" in sitemap:
        raise RuntimeError("sitemap ainda contém lastmod artificial do build")
    for url in EXCLUIR_SITEMAP:
        if url in sitemap:
            raise RuntimeError(f"URL que deveria estar fora do sitemap ainda presente: {url}")

    busca = (PUBLIC / "busca" / "index.html").read_text(encoding="utf-8")
    if '<meta name="robots" content="noindex, follow">' not in busca:
        raise RuntimeError("/busca/ não está com noindex, follow")


def main():
    ajustar_busca_noindex()
    ajustar_sitemap()
    validar_canonicals()
    validar_robots()
    validar_resultado()
    print("SEO P0 OK: /busca/ noindex, sitemap limpo, canonical e robots validados.")


if __name__ == "__main__":
    main()
