#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build específico para o deploy de produção no Vercel.

O GitHub Pages publica o projeto em /walterihoshi, mas o Vercel publica na raiz.
Este build ajusta apenas a cópia efêmera do checkout do Vercel antes de chamar
o gerador existente, sem alterar a configuração persistida usada pelo Pages.
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "data" / "config.json"


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg["site_url"] = "https://walterihoshi.vercel.app"
    cfg["base_path"] = ""
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run([sys.executable, str(RAIZ / "scripts" / "gerar.py")], cwd=RAIZ, check=True)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "seo_p0.py")], cwd=RAIZ, check=True)

    index = RAIZ / "public" / "index.html"
    if not index.exists():
        raise RuntimeError("Build do Vercel não gerou public/index.html")

    html = index.read_text(encoding="utf-8")
    if 'href="/static/estilo.css"' not in html:
        raise RuntimeError("HTML do Vercel não referencia /static/estilo.css")
    if '/walterihoshi/static/estilo.css' in html:
        raise RuntimeError("Build do Vercel ainda contém base_path do GitHub Pages")
    if '<link rel="canonical" href="https://walterihoshi.vercel.app/">' not in html:
        raise RuntimeError("Canonical da home não aponta para o domínio de produção")

    css = RAIZ / "public" / "static" / "estilo.css"
    if not css.exists() or css.stat().st_size < 1000:
        raise RuntimeError("CSS principal não foi copiado para public/static/estilo.css")

    sitemap = RAIZ / "public" / "sitemap.xml"
    if not sitemap.exists() or "https://walterihoshi.vercel.app/" not in sitemap.read_text(encoding="utf-8"):
        raise RuntimeError("Sitemap de produção ausente ou com domínio incorreto")

    robots = RAIZ / "public" / "robots.txt"
    if not robots.exists() or "https://walterihoshi.vercel.app/sitemap.xml" not in robots.read_text(encoding="utf-8"):
        raise RuntimeError("robots.txt não aponta para o sitemap de produção")

    print("Build Vercel OK: raiz /, CSS correto, SEO P0 validado e output em public/.")


if __name__ == "__main__":
    main()
