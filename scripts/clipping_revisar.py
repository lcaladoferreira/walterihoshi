#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

RAIZ=Path(__file__).resolve().parent.parent
HTML=RAIZ/'public'/'clipping'/'index.html'

NOVO_FORM='''<form class="filtros" id="filtros-clipping-v2" aria-label="Filtrar clipping">
<div class="filtros-linha">
<div class="campo"><label for="clip-texto-v2">Buscar no clipping</label><input id="clip-texto-v2" type="search" autocomplete="off" placeholder="Título, veículo, cidade ou assunto"></div>
<div class="campo"><label for="clip-periodo">Período</label><select id="clip-periodo"><option value="hoje" selected>Hoje</option><option value="7">Últimos 7 dias</option><option value="30">Últimos 30 dias</option><option value="tudo">Tudo</option></select></div>
<div class="campo"><label for="clip-fonte-v2">Fonte</label><select id="clip-fonte-v2"><option value="todas" selected>Todas</option><option value="imprensa">Imprensa</option><option value="oficial">Oficial / institucional</option></select></div>
</div>
<div class="filtros-rodape"><p class="filtro-contagem" id="clip-contagem-v2" role="status" aria-live="polite"></p></div>
</form><p id="clip-aviso-v2" class="estado estado-vazio" hidden></p>'''

def main():
    if not HTML.exists():
        print('Clipping UX: página não encontrada; nada a fazer.')
        return 0
    html=HTML.read_text(encoding='utf-8')
    html,n=re.subn(r'<form class="filtros" id="filtros-clipping".*?</form>',NOVO_FORM,html,count=1,flags=re.S)
    if n!=1:
        raise RuntimeError('Não foi possível substituir o painel antigo do clipping')
    script='<script src="/static/clipping-v2.js?v=20260915-clip2" defer></script>'
    if script not in html:
        html=html.replace('</body>',script+'</body>',1)
    HTML.write_text(html,encoding='utf-8')
    print('Clipping UX OK: filtros simplificados e Hoje como padrão.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
