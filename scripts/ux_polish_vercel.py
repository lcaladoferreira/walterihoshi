#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica correções de UX no artefato final do Vercel sem alterar o HTML estrutural."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
APP = PUBLIC / "static" / "app.js"
CSS = PUBLIC / "static" / "estilo.css"
POLISH = RAIZ / "static" / "ux-polish.css"
ASSET_VERSION = "20260915-ux3"


def replace_once(texto, antigo, novo, rotulo):
    if antigo not in texto:
        raise RuntimeError(f"Patch de UX não encontrou trecho esperado: {rotulo}")
    return texto.replace(antigo, novo, 1)


def main():
    js = APP.read_text(encoding="utf-8")

    js = replace_once(
        js,
        'if (e.q && normalizar(cartao.getAttribute("data-texto")).indexOf(e.q) === -1) return false;',
        'if (e.q) {\n'
        '        var haystack = normalizar(cartao.getAttribute("data-texto"));\n'
        '        var termosFiltro = e.q.split(/\\s+/).filter(Boolean);\n'
        '        if (!termosFiltro.every(function (termo) { return haystack.indexOf(termo) !== -1; })) return false;\n'
        '      }',
        "texto das realizações",
    )

    js = replace_once(
        js,
        'if (q && normalizar(li.getAttribute("data-texto")).indexOf(q) === -1) ok = false;',
        'if (q) {\n'
        '          var textoClip = normalizar(li.getAttribute("data-texto"));\n'
        '          var termosClip = q.split(/\\s+/).filter(Boolean);\n'
        '          if (!termosClip.every(function (termo) { return textoClip.indexOf(termo) !== -1; })) ok = false;\n'
        '        }',
        "texto do clipping",
    )

    js = replace_once(
        js,
        'itens[parseInt(b.getAttribute("data-tag"), 10)].acao();\n          aplicar();',
        'itens[parseInt(b.getAttribute("data-tag"), 10)].acao();\n          visiveis = PASSO;\n          aplicar();',
        "remoção de tag de filtro",
    )

    js = replace_once(
        js,
        'lerUrl();\n    aplicar();',
        'lerUrl();\n    aplicar();\n\n'
        '    window.addEventListener("popstate", function () {\n'
        '      if (campoTexto) campoTexto.value = "";\n'
        '      if (campoTema) campoTema.value = "";\n'
        '      if (campoMunicipio) campoMunicipio.value = "";\n'
        '      if (campoEvidencia) campoEvidencia.value = "0";\n'
        '      if (campoOrdem) campoOrdem.value = "relevancia";\n'
        '      caixasTipo.forEach(function (c) { c.checked = false; });\n'
        '      visiveis = PASSO;\n'
        '      lerUrl();\n'
        '      aplicar();\n'
        '    });',
        "histórico dos filtros",
    )

    APP.write_text(js, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8")
    extra = POLISH.read_text(encoding="utf-8")
    marcador = "/* UX-POLISH-VERCEL */"
    if marcador not in css:
        CSS.write_text(css + "\n\n" + marcador + "\n" + extra + "\n", encoding="utf-8")

    # Cache busting: mantém os mesmos elementos <link>/<script>, alterando só a URL
    # dos assets para garantir que o navegador/Vercel busque a versão nova.
    html_alterados = 0
    for html_path in PUBLIC.rglob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        novo = html.replace(
            'href="/static/estilo.css"',
            f'href="/static/estilo.css?v={ASSET_VERSION}"',
        ).replace(
            'src="/static/app.js"',
            f'src="/static/app.js?v={ASSET_VERSION}"',
        )
        if novo != html:
            html_path.write_text(novo, encoding="utf-8")
            html_alterados += 1

    if "termosFiltro.every" not in APP.read_text(encoding="utf-8"):
        raise RuntimeError("Patch de filtro de realizações não foi aplicado")
    if "UX-POLISH-VERCEL" not in CSS.read_text(encoding="utf-8"):
        raise RuntimeError("Camada de organização visual não foi aplicada")
    if html_alterados == 0:
        raise RuntimeError("Cache busting não foi aplicado em nenhum HTML")

    home = (PUBLIC / "index.html").read_text(encoding="utf-8")
    if f'/static/estilo.css?v={ASSET_VERSION}' not in home:
        raise RuntimeError("Home não referencia a versão nova do CSS")
    if f'/static/app.js?v={ASSET_VERSION}' not in home:
        raise RuntimeError("Home não referencia a versão nova do JS")

    print(f"UX Vercel OK: organização visual forte, filtros corrigidos e assets versionados em {html_alterados} HTMLs.")


if __name__ == "__main__":
    main()
