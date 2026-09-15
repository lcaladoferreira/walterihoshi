#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incorpora o CSS principal em todos os HTMLs gerados em public/.

Objetivo: garantir que o site mantenha layout e responsividade mesmo quando
um host, proxy ou configuração de Pages não resolver corretamente o caminho
externo /walterihoshi/static/estilo.css.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
CSS = RAIZ / "static" / "estilo.css"
MARCADOR = '<link rel="stylesheet" href="/walterihoshi/static/estilo.css">'


def main():
    css = CSS.read_text(encoding="utf-8")
    inline = '<style data-inline-css="estilo.css">\n' + css + '\n</style>'
    alterados = 0

    for html_path in PUBLIC.rglob("*.html"):
        texto = html_path.read_text(encoding="utf-8")
        if 'data-inline-css="estilo.css"' in texto:
            continue
        if MARCADOR not in texto:
            raise RuntimeError(f"link principal de CSS não encontrado em {html_path}")
        texto = texto.replace(MARCADOR, MARCADOR + "\n" + inline, 1)
        html_path.write_text(texto, encoding="utf-8")
        alterados += 1

    if alterados == 0:
        raise RuntimeError("nenhum HTML recebeu CSS inline")

    print(f"CSS incorporado em {alterados} páginas HTML.")


if __name__ == "__main__":
    main()
