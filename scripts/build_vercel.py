#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "data" / "config.json"
PRODUCTION_DOMAIN = "https://acervowalterihoshi.lcfconsulting.com.br"


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cfg["site_url"] = PRODUCTION_DOMAIN
    cfg["base_path"] = ""
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run([sys.executable, str(RAIZ / "scripts" / "gerar.py")], cwd=RAIZ, check=True)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "clipping_status.py")], cwd=RAIZ, check=True)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "clipping_revisar.py")], cwd=RAIZ, check=True)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "seo_p0.py")], cwd=RAIZ, check=True)
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "ux_polish_vercel.py")], cwd=RAIZ, check=True)

    index = RAIZ / "public" / "index.html"
    if not index.exists():
        raise RuntimeError("Build do Vercel não gerou public/index.html")
    html = index.read_text(encoding="utf-8")
    if '/static/estilo.css' not in html:
        raise RuntimeError("HTML do Vercel não referencia /static/estilo.css")
    if '/walterihoshi/static/estilo.css' in html:
        raise RuntimeError("Build do Vercel ainda contém base_path do GitHub Pages")
    if f'<link rel="canonical" href="{PRODUCTION_DOMAIN}/">' not in html:
        raise RuntimeError("Canonical da home não aponta para o domínio de produção")

    clipping = RAIZ / "public" / "clipping" / "index.html"
    if clipping.exists():
        ch = clipping.read_text(encoding="utf-8")
        for esperado in ("Última atualização do clipping:", "clip-periodo", "clip-fonte-v2", "clipping-v2.js"):
            if esperado not in ch:
                raise RuntimeError("Clipping funcional incompleto: %s ausente" % esperado)

    css = RAIZ / "public" / "static" / "estilo.css"
    if not css.exists() or css.stat().st_size < 1000:
        raise RuntimeError("CSS principal não foi copiado")
    app = RAIZ / "public" / "static" / "app.js"
    if not app.exists() or "termosFiltro.every" not in app.read_text(encoding="utf-8"):
        raise RuntimeError("Correções de filtro não foram aplicadas")

    sitemap = RAIZ / "public" / "sitemap.xml"
    if not sitemap.exists() or f"{PRODUCTION_DOMAIN}/" not in sitemap.read_text(encoding="utf-8"):
        raise RuntimeError("Sitemap de produção ausente ou incorreto")
    robots = RAIZ / "public" / "robots.txt"
    if not robots.exists() or f"{PRODUCTION_DOMAIN}/sitemap.xml" not in robots.read_text(encoding="utf-8"):
        raise RuntimeError("robots.txt não aponta para o sitemap de produção")

    print("Build Vercel OK: domínio oficial, sitemap, robots, clipping, SEO e UX validados.")


if __name__ == "__main__":
    main()
