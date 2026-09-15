#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parent.parent
HTML = RAIZ / 'public' / 'clipping' / 'index.html'

NOVO_FORM = '''<form class="filtros" id="filtros-clipping-v2" aria-label="Filtrar clipping">
<div class="filtros-linha">
<div class="campo"><label for="clip-texto-v2">Buscar no clipping</label><input id="clip-texto-v2" type="search" autocomplete="off" placeholder="Título, veículo, cidade ou assunto"></div>
<div class="campo"><label for="clip-periodo">Período</label><select id="clip-periodo"><option value="hoje">Hoje</option><option value="7" selected>Últimos 7 dias</option><option value="30">Últimos 30 dias</option><option value="tudo">Tudo</option></select></div>
<div class="campo"><label for="clip-fonte-v2">Fonte</label><select id="clip-fonte-v2"><option value="todas" selected>Todas</option><option value="imprensa">Imprensa</option><option value="oficial">Oficial / institucional</option></select></div>
</div>
<div class="filtros-rodape"><p class="filtro-contagem" id="clip-contagem-v2" role="status" aria-live="polite"></p></div>
</form><p id="clip-aviso-v2" class="dica clip-aviso-v2" hidden></p>'''


def ocultar_estado_vazio_legado(html):
    """Oculta o estado vazio antigo que o gerador ainda inclui após o formulário."""
    frase = 'Nenhuma menção com esse filtro'
    pos = html.find(frase)
    if pos < 0:
        return html
    inicio = html.rfind('<div class="estado estado-vazio"', 0, pos)
    if inicio < 0:
        return html
    fim_abertura = html.find('>', inicio)
    if fim_abertura < 0:
        return html
    abertura = html[inicio:fim_abertura + 1]
    if ' hidden' not in abertura:
        nova = abertura[:-1] + ' hidden data-clipping-legado="1">'
        html = html[:inicio] + nova + html[fim_abertura + 1:]
    return html


def main():
    if not HTML.exists():
        print('Clipping UX: página não encontrada; nada a fazer.')
        return 0

    html = HTML.read_text(encoding='utf-8')

    html, n = re.subn(
        r'<form class="filtros" id="filtros-clipping".*?</form>',
        NOVO_FORM,
        html,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError('Não foi possível substituir o painel antigo do clipping')

    # O período substitui a antiga navegação por dia. Mantê-la cria chips
    # redundantes e quebrados visualmente no mobile (ex.: "Ontem1").
    html = re.sub(
        r'<nav class="filtro-anos" data-navegacao-secoes[^>]*>.*?</nav>',
        '',
        html,
        count=1,
        flags=re.S,
    )

    html = ocultar_estado_vazio_legado(html)

    script = '<script src="/static/clipping-v2.js?v=20260915-clip3" defer></script>'
    html = re.sub(
        r'<script src="/static/clipping-v2\.js\?v=[^"]+" defer></script>',
        '',
        html,
    )
    html = html.replace('</body>', script + '</body>', 1)

    HTML.write_text(html, encoding='utf-8')

    if 'Nenhuma menção com esse filtro' in html and 'data-clipping-legado="1"' not in html:
        raise RuntimeError('Estado vazio legado do clipping continua visível')
    if 'data-navegacao-secoes aria-label="Ir para um dia"' in html:
        raise RuntimeError('Navegação redundante por dia continua presente')
    if '<option value="7" selected>' not in html:
        raise RuntimeError('Últimos 7 dias não ficou como período padrão')

    print('Clipping UX OK: sem estado vazio legado, sem chips de data e com 7 dias como padrão.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
