#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador do Acervo de Atuação Pública de Walter Ihoshi.

Gera um site estático em public/ a partir dos dados estruturados em data/.
SEO-first: HTML semântico, JSON-LD, Open Graph, canonical, sitemap, robots e RSS.
Dependências: apenas a biblioteca padrão do Python 3.
"""
import html
import json
import os
import re
import shutil
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "data")
SAIDA = os.path.join(RAIZ, "public")
STATIC = os.path.join(RAIZ, "static")

HOJE = date.today().isoformat()

# ---------------------------------------------------------------- carregamento
def carregar(nome):
    with open(os.path.join(DADOS, nome), encoding="utf-8") as f:
        return json.load(f)

CFG = carregar("config.json")
PESSOA = carregar("pessoa.json")
FONTES = carregar("fontes.json")
REALIZACOES = carregar("realizacoes.json")["realizacoes"]
TEMAS = carregar("temas.json")["temas"]
MUNICIPIOS = carregar("municipios.json")["municipios"]
TIMELINE = carregar("timeline.json")["eventos"]
ELEICOES = carregar("eleicoes.json")
ATUALIZACOES = carregar("atualizacoes.json")["atualizacoes"]

_clip_raw = None
_clip_path = os.path.join(DADOS, "monitoramento", "clipping.json")
if os.path.exists(_clip_path):
    with open(_clip_path, encoding="utf-8") as _f:
        _clip_raw = json.load(_f)
CLIPPING = (_clip_raw or {}).get("itens", [])
CLIPPING_ATUALIZADO_EM = (_clip_raw or {}).get("atualizado_em")

F = {f["id"]: f for f in FONTES["fontes"]}
R = {r["id"]: r for r in REALIZACOES}
T = {t["id"]: t for t in TEMAS}
M = {m["id"]: m for m in MUNICIPIOS}

BASE = CFG["base_path"].rstrip("/")
SITE = CFG["site_url"].rstrip("/") + BASE
PARTIDO_NUM = CFG["candidatura_2026"]

# ---------------------------------------------------------------- utilidades
def esc(s):
    return html.escape(str(s), quote=True)

def u(caminho):
    """URL absoluta (canonical/OG/sitemap)."""
    return SITE + caminho

def l(caminho):
    """href com base_path do projeto (portável entre hospedagens)."""
    return BASE + caminho

def fmt_data(iso):
    if not iso:
        return "—"
    try:
        a, m, d = iso.split("-")
        return "%s/%s/%s" % (d, m, a)
    except ValueError:
        return iso

def fonte_link(fid):
    f = F.get(fid)
    if not f:
        return '<span class="fonte">[fonte %s não catalogada]</span>' % esc(fid)
    nivel = f.get("nivel", 0)
    return (
        '<div class="fonte-item">'
        '<a href="%s" rel="nofollow noopener" target="_blank">%s</a>'
        '<span class="fonte-meta">%s &middot; nível de evidência %s &middot; consultada em %s</span>'
        "%s</div>"
        % (
            esc(f["url"]), esc(f["nome"]), esc(f["tipo"]), nivel,
            fmt_data(f.get("consultada_em", "")),
            ('<span class="fonte-nota">Nota: %s</span>' % esc(f["nota"])) if f.get("nota") else "",
        )
    )

def badge_evidencia(score):
    rotulos = [
        (100, "Documento oficial", "ev-oficial"),
        (90, "Base oficial", "ev-base"),
        (80, "Publicação institucional", "ev-inst"),
        (70, "Imprensa profissional", "ev-imprensa"),
        (60, "Fonte própria / declaração", "ev-propria"),
    ]
    for corte, rotulo, classe in rotulos:
        if score >= corte:
            return ('<span class="badge %s" title="Nível de evidência %s/100">Evidência %s &middot; %s'
                    '<span class="ev-meter"><span style="width:%d%%"></span></span></span>'
                    % (classe, score, score, rotulo, score))
    return ('<span class="badge ev-baixa" title="Nível de evidência %s/100">Evidência %s'
            '<span class="ev-meter"><span style="width:%d%%"></span></span></span>' % (score, score, score))

def chip_temas(temas_ids):
    return "".join(
        '<a class="chip" href="%s">%s</a>' % (l("/temas/%s/" % t), esc(T[t]["nome"]))
        for t in temas_ids if t in T
    )

def chip_municipios(ids):
    return "".join(
        '<a class="chip chip-loc" href="%s">%s</a>' % (l("/municipios/%s/" % m), esc(M[m]["nome"]))
        for m in ids if m in M
    )

def tipo_rotulo(tipo):
    mapa = {
        "AUTORIA": "Autoria", "RELATORIA": "Relatoria", "VOTO": "Voto", "ARTICULAÇÃO": "Articulação",
        "GESTÃO": "Gestão", "CONVÊNIO": "Convênio", "PROJETO": "Projeto", "LEI": "Lei", "EMENDA": "Emenda",
        "EVENTO": "Evento", "REUNIÃO": "Reunião", "POSICIONAMENTO": "Posicionamento", "PROPOSTA": "Proposta",
        "ENTREVISTA": "Entrevista", "AÇÃO INSTITUCIONAL": "Ação institucional",
    }
    return mapa.get(tipo, tipo)

EMOJI_TEMAS = {
    "micro-e-pequenas-empresas": "🏪", "empreendedorismo": "🚀", "desburocratizacao": "⚡",
    "comercio": "🛒", "credito": "💳", "cadastro-positivo": "✅", "desenvolvimento-economico": "📈",
    "saude": "🏥", "defesa-do-consumidor": "🧾", "administracao-publica": "🏛️", "convenios": "🤝",
    "comunidade-nikkei": "🎌", "relacoes-brasil-japao": "🌏", "seguranca": "🛡️", "educacao": "🎓",
}

def emoji_tema(tid):
    return EMOJI_TEMAS.get(tid, "📌")

# ---------------------------------------------------------------- JSON-LD
def jsonld_person():
    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": PESSOA["nome_civil"],
        "alternateName": PESSOA["variantes_busca"][:4],
        "birthDate": PESSOA["nascimento"],
        "birthPlace": {"@type": "Place", "name": "São Paulo, SP, Brasil"},
        "jobTitle": "Administrador",
        "description": PESSOA["resumo"],
        "nationality": "brasileira",
        "url": u("/"),
        "sameAs": PESSOA["sameAs"],
        "hasOccupation": [
            {
                "@type": "Occupation",
                "name": c["cargo"],
                "startDate": c["periodo"].split("(")[0].strip(),
            }
            for c in PESSOA["cargos"]
        ],
    }

def jsonld_website():
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": CFG["nome_projeto"],
        "url": u("/"),
        "inLanguage": "pt-BR",
        "description": CFG["descricao"],
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": u("/busca/") + "?q={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
    }

def jsonld_trilha(caminhos):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": nome, "item": u(caminho)}
            for i, (nome, caminho) in enumerate(caminhos)
        ],
    }

def jsonld_colecao(nome, descricao, caminho):
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": nome,
        "description": descricao,
        "url": u(caminho),
        "inLanguage": "pt-BR",
        "isPartOf": {"@type": "WebSite", "name": CFG["nome_projeto"], "url": u("/")},
    }

def jsonld_local(nome):
    return {
        "@context": "https://schema.org",
        "@type": "AdministrativeArea",
        "name": nome,
        "containedInPlace": {"@type": "AdministrativeArea", "name": "São Paulo, Brasil"},
        "url": u("/municipios/"),
    }

def jsonld_registro(r):
    citacoes = [F[fid]["url"] for fid in r["fontes"] if fid in F]
    doc = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": r["titulo"],
        "description": r["resumo"],
        "inLanguage": "pt-BR",
        "datePublished": r.get("data") or (r["periodo"][:4] if r.get("periodo") else None),
        "dateModified": HOJE,
        "mainEntityOfPage": u("/realizacoes/%s/" % r["id"]),
        "author": {"@type": "Organization", "name": CFG["nome_projeto"], "url": u("/")},
        "publisher": {"@type": "Organization", "name": CFG["nome_projeto"], "url": u("/")},
        "about": {"@type": "Person", "name": PESSOA["nome_civil"], "url": u("/")},
        "citation": citacoes,
    }
    if r.get("data"):
        doc["datePublished"] = r["data"]
    return doc

def bloco_jsonld(objetos):
    return "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(o, ensure_ascii=False)
        for o in objetos
    )

# ---------------------------------------------------------------- estrutura
# Arquitetura de informação: três agrupamentos por intenção de visita.
#   Acervo     → "o que foi feito" (a base e seus recortes)
#   Dossiês    → "aprofunde um capítulo" (páginas longas de contexto)
#   Acompanhe  → "o que está acontecendo e como conferir"
# No desktop os dois últimos viram menus reveláveis; no drawer mobile os três
# aparecem como seções rotuladas, sem esconder nada atrás de um toque.
GRUPOS_NAV = [
    ("Acervo", [
        ("/realizacoes/", "Realizações"),
        ("/temas/", "Temas"),
        ("/municipios/", "Municípios"),
        ("/linha-do-tempo/", "Linha do tempo"),
    ]),
    ("Dossiês", [
        ("/mandatos/", "Mandatos na Câmara"),
        ("/jucesp/", "Jucesp (2019–2023)"),
        ("/convenios/", "Convênios de SP"),
        ("/comunidade-nikkei/", "Comunidade nikkei"),
    ]),
    ("Acompanhe", [
        ("/clipping/", "Clipping do dia"),
        ("/atualizacoes/", "Atualizações do acervo"),
        ("/fontes/", "Fontes e método"),
    ]),
]

def contagens_nav():
    return {
        "/realizacoes/": "%d registros" % len(REALIZACOES),
        "/temas/": "%d temas" % len(TEMAS),
        "/municipios/": "%d municípios" % len(MUNICIPIOS),
        "/linha-do-tempo/": "%d marcos" % len(TIMELINE),
        "/clipping/": "%d menções" % len(CLIPPING),
        "/atualizacoes/": "%d incorporações" % len(ATUALIZACOES),
        "/fontes/": "%d fontes" % len(FONTES["fontes"]),
    }

def _link_nav(caminho, rotulo, atual, extra=""):
    atual_attr = ' aria-current="page"' if caminho == atual else ""
    return '<a class="nav-item%s" href="%s"%s>%s</a>' % (extra, l(caminho), atual_attr, esc(rotulo))

def _item_drawer(caminho, rotulo, atual, contagens):
    atual_attr = ' aria-current="page"' if caminho == atual else ""
    conta = contagens.get(caminho)
    return ('<li><a href="%s"%s>%s%s</a></li>'
            % (l(caminho), atual_attr, esc(rotulo),
               ('<span class="conta-mini">%s</span>' % esc(conta)) if conta else ""))

def cabecalho(atual):
    """Topo fixo: marca, atalho de busca, seletor de tema e navegação agrupada.
    Inclui o drawer mobile (foco preso, cortina, Esc) — sem JS o conteúdo
    continua acessível pelos links do rodapé e pela trilha de navegação."""
    contagens = contagens_nav()
    itens_desktop = []
    grupos_drawer = []

    for indice, (rotulo_grupo, itens) in enumerate(GRUPOS_NAV):
        esta_aberto = any(caminho == atual for caminho, _ in itens)
        if indice == 0:
            # Acervo: sempre visível, é o caminho principal
            for caminho, rotulo in itens:
                itens_desktop.append(_link_nav(caminho, rotulo, atual))
        else:
            subitens = "".join(
                '<li><a href="%s"%s>%s</a></li>'
                % (l(c), ' aria-current="page"' if c == atual else "", esc(r))
                for c, r in itens
            )
            itens_desktop.append(
                '<details class="nav-grupo"%s><summary>%s</summary>'
                '<ul class="nav-menu"><li class="nav-menu-nota">%s</li>%s</ul></details>'
                % (" open" if esta_aberto else "", esc(rotulo_grupo), esc(rotulo_grupo), subitens)
            )
        grupos_drawer.append(
            '<div class="drawer-grupo"><p class="drawer-grupo-titulo">%s</p><ul>%s</ul></div>'
            % (esc(rotulo_grupo), "".join(_item_drawer(c, r, atual, contagens) for c, r in itens))
        )

    return (
        '<header class="topo">'
        '<div class="topo-barra container">'
        '<a class="marca" href="%s"><span class="marca-nome">WALTER IHOSHI</span>'
        '<span class="marca-sub">Acervo de Atuação Pública</span></a>'
        '<nav class="nav-principal" aria-label="Navegação principal">%s</nav>'
        '<a class="util util-busca" href="%s"><span class="icone" aria-hidden="true">🔍</span>'
        '<span class="rotulo">Buscar</span></a>'
        '<button type="button" class="util util-tema" id="alternar-tema" '
        'aria-label="Tema: automático (segue o sistema) — ativar para mudar" title="Tema: automático">'
        '<span class="icone" aria-hidden="true">🌗</span></button>'
        '<button type="button" class="util util-menu" id="abrir-menu" aria-expanded="false" '
        'aria-controls="menu-lateral"><span class="icone" aria-hidden="true">☰</span>'
        '<span class="rotulo">Menu</span></button>'
        '</div></header>'
        '<button type="button" class="cortina" id="cortina-menu" tabindex="-1" '
        'aria-label="Fechar menu"></button>'
        '<div class="drawer" id="menu-lateral" role="dialog" aria-modal="true" '
        'aria-label="Menu de navegação" aria-hidden="true">'
        '<div class="drawer-cab"><span class="drawer-titulo">Navegar no acervo</span>'
        '<button type="button" class="drawer-fechar" id="fechar-menu">Fechar ✕</button></div>'
        '%s'
        '<div class="drawer-rodape">'
        '<a class="util" href="%s"><span class="icone" aria-hidden="true">🔍</span>'
        '<span class="rotulo">Buscar no acervo</span></a>'
        '<p class="rodape-resp">%s</p>'
        '</div></div>'
        % (
            l("/"), "".join(itens_desktop), l("/busca/"),
            "".join(grupos_drawer), l("/busca/"), rodape_responsavel(),
        )
    )

def rodape():
    """Rodapé como mapa de navegação secundário: garante saída para qualquer
    seção mesmo sem o menu do topo (e sem JavaScript)."""
    contagens = contagens_nav()
    colunas = "".join(
        '<div><p class="rodape-titulo">%s</p><ul>%s</ul></div>'
        % (esc(rotulo_grupo), "".join(_item_drawer(c, r, "", contagens) for c, r in itens))
        for rotulo_grupo, itens in GRUPOS_NAV
    )
    return (
        '<footer class="rodape"><div class="container">'
        '<div class="rodape-grade">'
        '<div><p class="rodape-titulo">%s</p><p>%s</p>'
        '<p class="rodape-links"><a href="%s" target="_blank" rel="noopener">Feed RSS</a> &middot; '
        '<a href="%s">Como o acervo é construído</a></p></div>'
        '%s'
        '</div>'
        '<div class="rodape-base">'
        '<p class="rodape-resp">%s</p>'
        "<p>Atualizado em %s &middot; Dados e código auditáveis no repositório público do projeto.</p>"
        '<p><a href="%s">↑ Voltar ao topo</a></p>'
        '</div></div></footer>'
        % (
            esc(CFG["nome_projeto"]), esc(CFG["descricao"]), l("/feed.xml"), l("/fontes/"),
            colunas, rodape_responsavel(), fmt_data(HOJE), l("/"),
        )
    )

def rodape_responsavel():
    autor = CFG.get("autor", {})
    resp = autor.get("responsavel", "")
    site = autor.get("site", "")
    partes = [esc(autor.get("tipo", ""))]
    if resp and "PREENCHER" not in resp:
        trecho = "Responsável pelo site: <strong>%s</strong>" % esc(resp)
        if site:
            trecho += ' &middot; <a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(site), esc(site.replace("https://", "").replace("http://", "").rstrip("/")))
        partes.append(trecho + ".")
    else:
        partes.append("Identificação do responsável pelo site a ser completada antes da publicação em período eleitoral (ver página de metodologia).")
    return " ".join(partes)

# ------------------------------------------------------------ sumário da página
def _ids_e_sumario(conteudo):
    """Garante id em todo <h2> e devolve a lista de seções para o sumário.
    Feito no build (não no navegador): o índice existe mesmo sem JavaScript."""
    itens = []
    sequencia = [0]

    def troca(m):
        attrs, miolo = m.group(1), m.group(2)
        existente = re.search(r'id="([^"]+)"', attrs)
        if existente:
            ident = existente.group(1)
        else:
            sequencia[0] += 1
            ident = "secao-%d" % sequencia[0]
            attrs = '%s id="%s"' % (attrs, ident)
        texto = html.unescape(re.sub(r"<[^>]+>", "", miolo)).strip()
        if texto:
            itens.append((ident, texto))
        return "<h2%s>%s</h2>" % (attrs, miolo)

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", troca, conteudo, flags=re.S), itens

def sumario_html(itens):
    if len(itens) < 3:
        return ""
    linhas = "".join('<li><a href="#%s">%s</a></li>' % (ident, esc(texto)) for ident, texto in itens)
    return ('<nav class="sumario" aria-label="Índice desta página">'
            '<p class="sumario-titulo">Nesta página</p><ol>%s</ol></nav>' % linhas)

def breadcrumb(itens):
    """Trilha de navegação como landmark real (<nav> + <ol>), não como texto solto."""
    if not itens:
        return ""
    celulas = "".join(
        '<li>%s</li>'
        % ('<a href="%s">%s</a>' % (l(caminho), esc(nome)) if caminho
           else '<span aria-current="page">%s</span>' % esc(nome))
        for nome, caminho in itens
    )
    return '<nav class="trilha" aria-label="Trilha de navegação"><ol>%s</ol></nav>' % celulas

# Tema aplicado antes da primeira pintura: evita o "flash" de tema errado.
JS_TEMA_ANTIFLASH = (
    "(function(){try{var t=localStorage.getItem('wi-tema');"
    "if(t){document.documentElement.setAttribute('data-tema',t);}}catch(e){}})();"
)

def pagina(caminho, titulo, descricao, conteudo, jsonld, og_tipo="website", trilha=None,
           sumario=True):
    """Monta e grava uma página HTML completa (estrutura, estados e atalhos)."""
    if trilha:
        jsonld = list(jsonld) + [jsonld_trilha(trilha)]

    corpo = conteudo
    lateral = ""
    # Sumário só onde a página é longa o bastante para precisar de um.
    if sumario and len(conteudo) >= 6000:
        corpo, secoes = _ids_e_sumario(conteudo)
        lateral = sumario_html(secoes)

    classe_pagina = "pagina pagina--com-lateral" if lateral else "pagina"
    aside = ('<aside class="pagina-lateral">%s</aside>' % lateral) if lateral else ""

    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt-BR" class="sem-js" data-tema="auto">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n"
        '<meta name="description" content="%s">\n'
        '<link rel="canonical" href="%s">\n'
        '<meta name="robots" content="index, follow">\n'
        '<meta property="og:type" content="%s">\n'
        '<meta property="og:locale" content="pt_BR">\n'
        '<meta property="og:site_name" content="%s">\n'
        '<meta property="og:title" content="%s">\n'
        '<meta property="og:description" content="%s">\n'
        '<meta property="og:url" content="%s">\n'
        '<meta property="og:image" content="%s">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="theme-color" content="#101f38">\n'
        '<link rel="icon" type="image/svg+xml" href="%s">\n'
        '<link rel="stylesheet" href="%s">\n'
        '<link rel="alternate" type="application/rss+xml" title="%s" href="%s">\n'
        '<script>%s</script>\n'
        "%s\n</head>\n<body>\n"
        '<a class="pular-conteudo" href="#conteudo">Pular para o conteúdo</a>\n'
        '<div class="progresso" id="progresso-leitura" aria-hidden="true"></div>\n'
        "%s\n"
        '<main id="conteudo" tabindex="-1"><div class="container %s">'
        '<div class="pagina-corpo">%s</div>%s</div></main>\n'
        "%s\n"
        '<button type="button" class="voltar-topo" id="voltar-topo" aria-label="Voltar ao topo">'
        '<span aria-hidden="true">↑</span></button>\n'
        '<p class="sr-only" role="status" aria-live="polite" id="avisos"></p>\n'
        '<script src="%s" defer></script>\n'
        "</body>\n</html>"
    ) % (
        esc(titulo), esc(descricao), u(caminho), og_tipo,
        esc(CFG["nome_projeto"]), esc(titulo), esc(descricao), u(caminho),
        u("/static/og.png"), l("/static/favicon.svg"),
        l("/static/estilo.css"),
        esc(CFG["nome_projeto"]), l("/feed.xml"),
        JS_TEMA_ANTIFLASH,
        bloco_jsonld(jsonld),
        cabecalho(caminho),
        classe_pagina, corpo, aside,
        rodape(),
        l("/static/app.js"),
    )
    if caminho.endswith(".html"):
        destino = os.path.join(SAIDA, caminho.lstrip("/"))
    else:
        destino = os.path.join(SAIDA, caminho.lstrip("/"), "index.html") if caminho != "/" \
            else os.path.join(SAIDA, "index.html")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html_doc)

def texto_busca_cartao(r):
    """Cadeia indexável do cartão (usada pelos filtros client-side)."""
    partes = [r["titulo"], r["resumo"], r.get("tipo_detalhe", ""), r.get("periodo", ""), r["cargo"]]
    partes += [T[t]["nome"] for t in r["temas"] if t in T]
    partes += [M[m]["nome"] for m in r["municipios"] if m in M]
    partes += r.get("entidades", [])
    return " ".join(p for p in partes if p).lower()

def card_registro(r, ordem=0):
    """Cartão de registro. O cartão inteiro é clicável (link esticado) e o
    título continua sendo o único ponto de foco do teclado — sem duplicar
    parada de tabulação."""
    when = r.get("data") or (r.get("periodo") or "")
    return (
        '<article class="card" data-id="%s" data-tipo="%s" data-temas="%s" data-municipios="%s" '
        'data-ev="%s" data-data="%s" data-ordem="%d" data-titulo="%s" data-texto="%s">'
        '<div class="card-tags"><span class="tag-tipo">%s</span>%s</div>'
        '%s'
        '<h3><a href="%s">%s</a></h3>'
        "<p>%s</p>"
        '<p class="card-meta">%s%s</p>'
        '<span class="card-link">Ver registro completo com fontes &rarr;</span>'
        "</article>"
        % (
            esc(r["id"]), esc(r["tipo"]),
            esc(" ".join(r["temas"])), esc(" ".join(r["municipios"])),
            esc(r["evidence_score"]), esc(r.get("data", "")), ordem,
            esc(r["titulo"]), esc(texto_busca_cartao(r)),
            esc(tipo_rotulo(r["tipo"])), badge_evidencia(r["evidence_score"]),
            ('<p class="card-data"><time datetime="%s">%s</time></p>'
             % (esc(r["data"]), esc(fmt_data(r["data"])))) if r.get("data")
            else ('<p class="card-data">%s</p>' % esc(when) if when else ""),
            l("/realizacoes/%s/" % r["id"]), esc(r["titulo"]),
            esc(r["resumo"]),
            chip_temas(r["temas"]), chip_municipios(r["municipios"]),
        )
    )

def estado_vazio(titulo, texto, acoes=""):
    """Estado vazio com caminho de saída — nunca uma tela morta."""
    return ('<div class="estado estado-vazio"><p class="estado-titulo">%s</p><p>%s</p>%s</div>'
            % (esc(titulo), esc(texto),
               ('<div class="estado-acoes">%s</div>' % acoes) if acoes else ""))

def lista_registros(registros, vazio="Nenhum registro documentado nesta coleção nesta versão do acervo."):
    if not registros:
        return estado_vazio(
            "Nada documentado aqui (ainda)", vazio,
            '<a class="btn btn-fantasma" href="%s">Ver todas as realizações</a>'
            '<a class="btn" href="%s">Como o acervo é construído</a>' % (l("/realizacoes/"), l("/fontes/")),
        )
    cards = "".join(card_registro(r, i) for i, r in enumerate(registros))
    return '<div class="grade">%s</div>' % cards

def tabela_responsiva(rotulo, colunas, corpo, dica="Tabela rolável — arraste para o lado para ver todas as colunas."):
    """Tabela sempre dentro de um bloco rolável, focável e rotulado.

    Sem o contêiner, uma tabela mais larga que o conteúdo faz a **página inteira**
    rolar para o lado em telas pequenas (medido em /mandatos/ e /fontes/ a 320px).
    Com ele, a rolagem fica contida no bloco. `tabindex="0"` + `role="region"` +
    `aria-label` mantêm a rolagem alcançável por teclado e leitor de tela
    (WCAG 2.1.1 e 1.4.10), e a dica só aparece onde a tabela pode rolar.
    """
    return (
        '<div class="tabela-wrap" role="region" tabindex="0" aria-label="%s">'
        '<table class="tabela"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
        '</div><p class="tabela-dica">%s</p>'
        % (esc(rotulo),
           "".join('<th scope="col">%s</th>' % esc(c) for c in colunas),
           corpo, esc(dica))
    )


def sec_fontes(ids, titulo="Fontes desta seção"):
    return '<section class="secao-fontes"><h2>%s</h2>%s</section>' % (
        esc(titulo), "".join(fonte_link(fid) for fid in ids)
    )

# ---------------------------------------------------------------- páginas
def pag_home():
    destaques = [r for r in REALIZACOES if r.get("destaque")]
    conteudo = (
        '<section class="hero">'
        "<p class='hero-eyebrow'>Base pública e verificável</p>"
        "<h1>Walter Ihoshi</h1>"
        "<p class='hero-sub'>Uma trajetória de trabalho por São Paulo, documentada em fonte por fonte.</p>"
        "<p class='hero-texto'>Explore projetos, ações, realizações, mandatos, municípios e documentos que registram "
        "a atuação pública de <strong>Walter Shindi Iihoshi</strong> — três mandatos na Câmara dos Deputados "
        "(2007–2019), presidência da Jucesp (2019–2023) e diretoria de convênios do Governo de São Paulo (2023–2026).</p>"
        '<form class="busca-destaque" action="%s" method="get">'
        '<input type="search" name="q" placeholder="Município, projeto ou tema" aria-label="Pesquisar no acervo">'
        "<button type='submit'>Pesquisar no acervo</button></form>"
        '<p class="hero-exemplos">Experimente: '
        '<a href="%s">JUCESP</a> &middot; <a href="%s">Cadastro Positivo</a> &middot; '
        '<a href="%s">Marília</a> &middot; <a href="%s">microempresas</a> &middot; '
        '<a href="%s">Japão</a> &middot; <a href="%s">desburocratização</a></p>'
        '<div class="atalhos">'
        '<a class="atalho" href="%s">Ver os %d registros documentados</a>'
        '<a class="atalho atalho-secundario" href="%s">Clipping do dia (%d menções)</a>'
        '<a class="atalho atalho-secundario" href="%s">Como cada fato é verificado</a>'
        '</div>'
        '<p class="hero-principio"><strong>%s</strong> — cada realização traz cargo, tipo de atuação e fontes consultadas.</p>'
        '<div class="hero-stats">'
        '<div class="stat"><b>%d</b><span>registros documentados</span></div>'
        '<div class="stat"><b>%d</b><span>fontes catalogadas</span></div>'
        '<div class="stat"><b>%d</b><span>temas</span></div>'
        '<div class="stat"><b>%d</b><span>municípios</span></div>'
        "</div>"
        "</section>"
        % (
            l("/busca/"),
            l("/busca/") + "?q=JUCESP", l("/busca/") + "?q=Cadastro+Positivo",
            l("/busca/") + "?q=Mar%C3%ADlia", l("/busca/") + "?q=microempresas",
            l("/busca/") + "?q=Jap%C3%A3o", l("/busca/") + "?q=desburocratiza%C3%A7%C3%A3o",
            l("/realizacoes/"), len(REALIZACOES),
            l("/clipping/"), len(CLIPPING),
            l("/fontes/"),
            esc(CFG["tagline"]),
            len(REALIZACOES), len(FONTES["fontes"]), len(TEMAS), len(MUNICIPIOS),
        )
    )
    conteudo += (
        '<section><div class="secao-cab"><h2>Destaques da trajetória</h2>'
        '<a class="ver-tudo" href="%s">Todas as realizações</a></div>%s</section>'
        % (l("/realizacoes/"), lista_registros(destaques))
    )
    # Temas
    cards_tema = "".join(
        '<a class="card-tema" href="%s"><h3><span class="tema-emoji">%s</span> %s</h3><p>%s</p><span>%d registro(s) documentado(s) &rarr;</span></a>'
        % (l("/temas/%s/" % t["id"]), emoji_tema(t["id"]), esc(t["nome"]), esc(t["resumo"][:150] + "…"), num_registros_tema(t["id"]))
        for t in TEMAS if not t.get("apenas_proposta")
    )
    conteudo += (
        '<section><div class="secao-cab"><h2>Atuação por tema</h2>'
        '<a class="ver-tudo" href="%s">Todos os temas</a></div><div class="grade-grade">%s</div></section>'
        % (l("/temas/"), cards_tema)
    )
    cards_mun = "".join(
        '<a class="card-tema" href="%s"><h3>%s</h3><p>%s</p><span>%d registro(s) &rarr;</span></a>'
        % (l("/municipios/%s/" % m["id"]), esc(m["nome"]), esc(m["resumo"][:150] + "…"), num_registros_municipio(m["id"]))
        for m in MUNICIPIOS
    )
    conteudo += (
        '<section><div class="secao-cab"><h2>Atuação por localidade</h2>'
        '<a class="ver-tudo" href="%s">Todos os municípios</a></div><div class="grade-grade">%s</div></section>'
        % (l("/municipios/"), cards_mun)
    )
    tl_resumo = "".join(
        '<li><strong>%s</strong> — %s <a href="%s">linha do tempo completa &rarr;</a></li>'
        % (esc(str(ev["ano"])), esc(ev["titulo"]), l("/linha-do-tempo/"))
        for ev in TIMELINE[:: max(1, len(TIMELINE) // 6)][:6]
    )
    conteudo += (
        '<section><div class="secao-cab"><h2>Linha do tempo</h2>'
        '<a class="ver-tudo" href="%s">Trajetória completa (1961–2026)</a></div>'
        '<ul class="tl-mini">%s</ul></section>' % (l("/linha-do-tempo/"), tl_resumo)
    )
    clip_ult = sorted(CLIPPING, key=lambda x: x.get("data", ""), reverse=True)[:5]
    if clip_ult:
        clip_html = "".join(
            '<li class="clip-item"><span class="clip-data">%s</span>'
            '<div><a href="%s" target="_blank" rel="noopener nofollow">%s</a>'
            '<p class="clip-meta">%s%s</p></div></li>'
            % (fmt_data(c.get("data")), esc(c["link"]), esc(c["titulo"]), esc(c.get("fonte", "")),
               (" &middot; " + esc(T[c["tema_proposto"]]["nome"])) if c.get("tema_proposto") and c["tema_proposto"] in T else "")
            for c in clip_ult
        )
        conteudo += (
            '<section><div class="secao-cab"><h2>Clipping — menções na imprensa</h2>'
            '<a class="ver-tudo" href="%s">Clipping completo</a></div>'
            '<p class="lead">Coleta diária automática de menções a Walter Ihoshi na imprensa e em fontes oficiais. '
            "Menções não são registros verificados do acervo.</p>"
            '<ul class="clip-lista">%s</ul></section>' % (l("/clipping/"), clip_html)
        )
    ups = sorted(ATUALIZACOES, key=lambda x: x["data"], reverse=True)[:3]
    ups_html = "".join(
        '<li><time>%s</time><strong>%s</strong><p>%s</p></li>'
        % (fmt_data(up["data"]), esc(up["titulo"]), esc(up["texto"]))
        for up in ups
    )
    conteudo += (
        '<section><div class="secao-cab"><h2>Últimas atualizações do acervo</h2>'
        '<a class="ver-tudo" href="%s">Todas as atualizações</a></div>'
        '<ul class="atualizacoes">%s</ul></section>' % (l("/atualizacoes/"), ups_html)
    )
    conteudo += (
        '<section class="secao-eleitoral"><h2>Sobre a natureza deste site</h2>'
        "<p>Este acervo é um projeto independente de documentação pública, com registros baseados exclusivamente em "
        "fontes citadas. Walter Ihoshi é candidato a %s pelo %s (nº %s) nas eleições de 2026; "
        "propostas de campanha <a href='%s'>ficam separadas</a> das realizações documentadas.</p></section>"
        % (esc(PARTIDO_NUM["cargo"]), esc(PARTIDO_NUM["partido"]), esc(PARTIDO_NUM["numero"]), l("/fontes/") + "#eleitoral")
    )
    pagina("/", CFG["nome_projeto"] + " — fatos verificáveis da trajetória de Walter Ihoshi",
           "O que Walter Ihoshi fez por São Paulo: realizações, projetos, relatorias, mandatos (2007–2019), "
           "Jucesp (2019–2023), convênios (2023–2026) e relação com a comunidade nikkei — com fontes verificáveis.",
           conteudo, [jsonld_person(), jsonld_website()], og_tipo="profile", sumario=False)

def num_registros_tema(tid):
    return sum(1 for r in REALIZACOES if tid in r["temas"])

def num_registros_municipio(mid):
    return sum(1 for r in REALIZACOES if mid in r["municipios"])

ORDEM_TIPOS = ["LEI", "RELATORIA", "EMENDA", "GESTÃO", "ARTICULAÇÃO", "CONVÊNIO",
               "AÇÃO INSTITUCIONAL", "PROPOSTA", "REUNIÃO", "EVENTO"]

def pag_realizacoes_lista():
    """Base completa com facetas. O HTML chega com os registros ordenados e
    visíveis; o JavaScript acrescenta filtro, ordenação, contagem e paginação
    progressiva, mantendo o estado na URL (filtros são compartilháveis)."""
    registros = sorted(
        REALIZACOES,
        key=lambda r: (ORDEM_TIPOS.index(r["tipo"]) if r["tipo"] in ORDEM_TIPOS else 99,
                       -(r.get("evidence_score") or 0), r["titulo"]),
    )
    por_tipo = {}
    for r in registros:
        por_tipo[r["tipo"]] = por_tipo.get(r["tipo"], 0) + 1
    tipos_ordenados = sorted(por_tipo, key=lambda t: (ORDEM_TIPOS.index(t) if t in ORDEM_TIPOS else 99, t))

    opcoes_tipo = "".join(
        '<label class="chip-opcao"><input type="checkbox" name="tipo" value="%s">'
        '<span>%s <span class="n">%d</span></span></label>'
        % (esc(t), esc(tipo_rotulo(t)), por_tipo[t])
        for t in tipos_ordenados
    )
    opcoes_tema = "".join(
        '<option value="%s">%s (%d)</option>' % (esc(t["id"]), esc(t["nome"]), num_registros_tema(t["id"]))
        for t in sorted(TEMAS, key=lambda x: x["nome"]) if num_registros_tema(t["id"])
    )
    opcoes_municipio = "".join(
        '<option value="%s">%s (%d)</option>' % (esc(m["id"]), esc(m["nome"]), num_registros_municipio(m["id"]))
        for m in sorted(MUNICIPIOS, key=lambda x: x["nome"]) if num_registros_municipio(m["id"])
    )

    filtros = (
        '<form class="filtros" id="filtros-realizacoes" data-navegacao-secoes aria-label="Filtrar registros">'
        '<div class="filtros-linha">'
        '<div class="campo"><label for="f-texto">Filtrar por texto</label>'
        '<input id="f-texto" name="q" type="search" autocomplete="off" '
        'placeholder="Título, órgão, lei, cidade…"></div>'
        '<div class="campo"><label for="f-tema">Tema</label>'
        '<select id="f-tema" name="tema"><option value="">Todos os temas</option>%s</select></div>'
        '<div class="campo"><label for="f-municipio">Município</label>'
        '<select id="f-municipio" name="municipio"><option value="">Todos os municípios</option>%s</select></div>'
        '<div class="campo"><label for="f-evidencia">Evidência mínima</label>'
        '<select id="f-evidencia" name="evidencia">'
        '<option value="0">Qualquer nível</option>'
        '<option value="60">60+ — declaração/fonte própria</option>'
        '<option value="70">70+ — imprensa profissional</option>'
        '<option value="80">80+ — publicação institucional</option>'
        '<option value="90">90+ — base oficial</option>'
        '<option value="100">100 — documento oficial</option></select></div>'
        '<div class="campo"><label for="f-ordem">Ordenar por</label>'
        '<select id="f-ordem" name="ordem">'
        '<option value="relevancia">Tipo de atuação (padrão)</option>'
        '<option value="recente">Mais recentes</option>'
        '<option value="antigo">Mais antigos</option>'
        '<option value="evidencia">Maior nível de evidência</option>'
        '<option value="titulo">Título (A–Z)</option></select></div>'
        '</div>'
        '<fieldset class="filtro-chips"><legend>Tipo de atuação</legend>'
        '<div class="opcoes">%s</div></fieldset>'
        '<ul class="filtros-aplicadas" id="filtros-aplicados"></ul>'
        '<div class="filtros-rodape">'
        '<p class="filtro-contagem" id="filtro-contagem" role="status" aria-live="polite"></p>'
        '<div class="filtro-acoes">'
        '<button type="button" class="btn btn-fantasma" id="limpar-filtros">Limpar filtros</button>'
        '<div class="densidade" role="group" aria-label="Densidade da lista">'
        '<button type="button" data-densidade="grade" aria-pressed="true">Grade</button>'
        '<button type="button" data-densidade="densa" aria-pressed="false">Lista</button>'
        '</div></div></div></form>'
        % (opcoes_tema, opcoes_municipio, opcoes_tipo)
    )

    aviso = estado_vazio(
        "Nenhum registro com esses filtros",
        "A combinação escolhida não corresponde a nenhum registro publicado. "
        "Isso não significa que a atuação não exista — significa que ainda não há fonte "
        "suficiente para publicá-la como fato.",
        '<button type="button" class="btn" id="limpar-filtros-2">Limpar filtros</button>'
        '<a class="btn btn-fantasma" href="%s">Ver metodologia e níveis de evidência</a>' % l("/fontes/"),
    ).replace('class="estado estado-vazio"', 'class="estado estado-vazio" id="filtro-aviso" hidden', 1)

    cards = "".join(card_registro(r, i) for i, r in enumerate(registros))
    conteudo = breadcrumb([("Início", "/"), ("Realizações", None)]) + (
        "<h1>Realizações — base completa</h1>"
        '<p class="lead">Cada registro identifica <strong>tipo de atuação</strong> (autoria, relatoria, gestão, '
        "articulação…), cargo exercido, período, resultado documentado e fontes com nível de evidência. "
        "Participação não é convertida em autoria; proposta não é apresentada como entrega.</p>"
        '<p class="dica">%d registros publicados nesta versão. Use os filtros para recortar por tipo, tema, '
        "município ou nível de evidência — o endereço da página guarda a sua combinação, então dá para "
        "compartilhar o recorte exato.</p>"
        "%s%s"
        "<h2>Registros documentados</h2>"
        '<div id="lista-registros"><div class="grade">%s</div></div>'
        '<div class="carregar-mais"><button type="button" class="btn" id="carregar-mais">'
        '<span>Mostrar mais registros</span></button></div>'
        % (len(registros), filtros, aviso, cards)
    )
    pagina("/realizacoes/", "O que Walter Ihoshi fez: realizações, projetos e ações documentadas",
           "Base completa de ações, projetos, entregas e atuações de Walter Ihoshi, cada uma com fonte, "
           "cargo, tipo de atuação e nível de evidência.", conteudo,
           [jsonld_colecao("Realizações de Walter Ihoshi", "Base completa de registros documentados.", "/realizacoes/")],
           trilha=[("Início", "/"), ("Realizações", "/realizacoes/")], sumario=False)

def registros_ordenados():
    """Mesma ordem usada na listagem — garante que "anterior/próximo"
    corresponda ao que o visitante viu na página de base."""
    return sorted(
        REALIZACOES,
        key=lambda r: (ORDEM_TIPOS.index(r["tipo"]) if r["tipo"] in ORDEM_TIPOS else 99,
                       -(r.get("evidence_score") or 0), r["titulo"]),
    )

def navegacao_registro(r):
    """Saída ao fim da leitura: nunca deixar o visitante num beco sem saída."""
    ordem = registros_ordenados()
    pos = [i for i, x in enumerate(ordem) if x["id"] == r["id"]]
    if not pos:
        return ""
    i = pos[0]
    anterior = ordem[i - 1] if i > 0 else None
    proximo = ordem[i + 1] if i < len(ordem) - 1 else None
    if not anterior and not proximo:
        return ""

    def celula(reg, classe, rotulo, seta):
        if not reg:
            return "<span></span>"
        return ('<a class="%s" href="%s" rel="%s"><span class="rotulo">%s</span>%s %s</a>'
                % (classe, l("/realizacoes/%s/" % reg["id"]), classe, esc(rotulo),
                   seta if classe == "anterior" else "", esc(reg["titulo"]) + ("" if classe == "anterior" else " " + seta)))

    return ('<nav class="anterior-proximo" aria-label="Outros registros da base">%s%s</nav>'
            % (celula(anterior, "anterior", "Registro anterior", "←"),
               celula(proximo, "proximo", "Próximo registro", "→")))

def pag_realizacao(r):
    proposicao = ""
    if r.get("proposicao"):
        p = r["proposicao"]
        link_api = ""
        if p.get("id_camara"):
            link_api = ' &middot; <a href="https://dadosabertos.camara.leg.br/api/v2/proposicoes/%s" target="_blank" rel="noopener">ficha na API da Câmara</a>' % p["id_camara"]
        proposicao = ("<dt>Proposição</dt><dd>%s%s%s</dd>" % (
            esc(p["sigla"]), (' — transformada em <strong>%s</strong>' % esc(p["norma"])) if p.get("norma") else "", link_api))
    nota_ev = ""
    if r.get("nota_evidencia"):
        nota_ev = '<p class="nota-evidencia"><strong>Nota de evidência:</strong> %s</p>' % esc(r["nota_evidencia"])
    relacionadas = ""
    if r.get("relacionadas"):
        relacionadas = '<section class="secao-rel"><h2>Outras ações relacionadas</h2><ul class="rel-lista">%s</ul></section>' % "".join(
            '<li><a href="%s">%s</a><span>%s</span></li>'
            % (l("/realizacoes/%s/" % rid), esc(R[rid]["titulo"]), esc(tipo_rotulo(R[rid]["tipo"])))
            for rid in r["relacionadas"] if rid in R
        )
    entidades = "".join("<li>%s</li>" % esc(e) for e in r.get("entidades", []))
    share_url = u("/realizacoes/%s/" % r["id"])
    texto_compartilhar = "%s — %s" % (r["titulo"], share_url)
    share = (
        '<div class="compartilhar"><span>Compartilhar:</span>'
        '<a href="https://wa.me/?text=%s" target="_blank" rel="noopener">WhatsApp</a>'
        '<a href="https://www.facebook.com/sharer/sharer.php?u=%s" target="_blank" rel="noopener">Facebook</a>'
        '<a href="https://www.linkedin.com/sharing/share-offsite/?url=%s" target="_blank" rel="noopener">LinkedIn</a>'
        '<button type="button" class="copiar" data-url="%s">Copiar link</button></div>'
        % (esc(texto_compartilhar.replace(" ", "%20")), esc(share_url), esc(share_url), esc(share_url))
    )
    conteudo = (
        '<article class="registro">'
        + breadcrumb([("Início", "/"), ("Realizações", "/realizacoes/"), (r["titulo"], None)]) +
        '<div class="card-tags"><span class="tag-tipo">%s</span>%s</div>'
        "<h1>%s</h1>"
        '<p class="lead">%s</p>%s'
        '<dl class="ficha">'
        "<dt>Quando</dt><dd>%s%s</dd>"
        "<dt>Cargo exercido</dt><dd>%s</dd>"
        "<dt>Tipo de atuação</dt><dd>%s — %s</dd>"
        "<dt>Localidades</dt><dd>%s</dd>"
        "<dt>Assuntos</dt><dd>%s</dd>"
        "%s"
        "</dl>"
        "<h2>O que aconteceu</h2><p>%s</p>"
        "<h2>Qual foi a participação de Walter Ihoshi</h2><p>%s</p>"
        "<h2>Por que o assunto era relevante</h2><p>%s</p>"
        "<h2>Resultado conhecido</h2><p>%s</p>"
        '<h2>Pessoas e instituições envolvidas</h2><ul class="entidades">%s</ul>'
        "%s"
        "</article>%s%s%s"
    ) % (
        esc(tipo_rotulo(r["tipo"])), badge_evidencia(r["evidence_score"]),
        esc(r["titulo"]), esc(r["resumo"]), nota_ev,
        fmt_data(r.get("data")), (' <span class="periodo">(%s)</span>' % esc(r["periodo"])) if r.get("periodo") else "",
        esc(r["cargo"]), esc(tipo_rotulo(r["tipo"])), esc(r.get("tipo_detalhe", "")),
        chip_municipios(r["municipios"]) or "—", chip_temas(r["temas"]) or "—",
        proposicao,
        esc(r["o_que_aconteceu"]), esc(r["participacao"]), esc(r["relevancia"]), esc(r["resultado"]),
        entidades or "<li>—</li>",
        sec_fontes(r["fontes"], "Documentos e fontes"),
        share, relacionadas, navegacao_registro(r),
    )
    pagina("/realizacoes/%s/" % r["id"],
           "%s" % r["titulo"],
           r["resumo"], conteudo,
           [jsonld_registro(r)],
           og_tipo="article",
           trilha=[("Início", "/"), ("Realizações", "/realizacoes/"), (r["titulo"], "/realizacoes/%s/" % r["id"])])

def pag_temas_lista():
    cards = "".join(
        '<a class="card-tema" href="%s"><h3><span class="tema-emoji">%s</span> %s</h3><p>%s</p><span>%s</span></a>'
        % (l("/temas/%s/" % t["id"]), emoji_tema(t["id"]), esc(t["nome"]), esc(t["resumo"]),
           ("Só proposta de campanha — sem realização documentada nesta versão" if t.get("apenas_proposta")
            else "%d registro(s) documentado(s) &rarr;" % num_registros_tema(t["id"])))
        for t in TEMAS
    )
    conteudo = breadcrumb([("Início", "/"), ("Temas", None)]) + (
        "<h1>Atuação por tema</h1>"
        '<p class="lead">Páginas temáticas reúnem os registros do acervo por assunto. Temas sem conteúdo documental '
        "suficiente não recebem página de realização — apenas indicação de existência de proposta eleitoral.</p>"
        "<h2>Temas do acervo</h2>"
        '<div class="grade-grade">%s</div>' % cards
    )
    pagina("/temas/", "Walter Ihoshi por tema: micro e pequenas empresas, crédito, saúde, desburocratização e mais",
           "Organização temática da atuação documentada de Walter Ihoshi.",
           conteudo, [jsonld_colecao("Temas", "Organização temática do acervo.", "/temas/")],
           trilha=[("Início", "/"), ("Temas", "/temas/")], sumario=False)

def pag_tema(t):
    regs = [r for r in REALIZACOES if t["id"] in r["temas"]]
    cargos = ", ".join(esc(c) for c in t["cargos"]) or "—"
    alerta = ""
    if t.get("apenas_proposta"):
        alerta = ('<div class="alerta"><strong>Transparência:</strong> nesta versão do acervo não há realização '
                  "documentada neste tema. Existe proposta de campanha para 2026, registrada como proposta — não como "
                  "entrega.</div>")
    conteudo = breadcrumb([("Início", "/"), ("Temas", "/temas/"), (t["nome"], None)]) + (
        "<h1><span class=\"tema-emoji grande\">%s</span> Walter Ihoshi e %s</h1>"
        '<p class="lead">%s</p>%s'
        '<dl class="ficha"><dt>Cargos em que atuou no tema</dt><dd>%s</dd>'
        "<dt>Registros documentados</dt><dd>%d</dd></dl>"
        "<h2>Principais ações documentadas</h2>%s"
        "<h2>Localidades relacionadas</h2><p>%s</p>"
        "%s"
    ) % (
        emoji_tema(t["id"]), esc(t["nome"]), esc(t["resumo"]), alerta,
        cargos, len(regs),
        lista_registros(regs, "Nenhum registro documentado neste tema nesta versão do acervo."),
        chip_municipios(sorted({m for r in regs for m in r["municipios"]})) or "—",
        sec_fontes(t["fontes"]),
    )
    pagina("/temas/%s/" % t["id"],
           "Walter Ihoshi e %s: ações e projetos documentados" % t["nome"],
           t["resumo"], conteudo,
           [jsonld_colecao("Walter Ihoshi e %s" % t["nome"], t["resumo"], "/temas/%s/" % t["id"])],
           trilha=[("Início", "/"), ("Temas", "/temas/"), (t["nome"], "/temas/%s/" % t["id"])])

def pag_municipios_lista():
    cards = "".join(
        '<a class="card-tema" href="%s"><h3>%s</h3><p>%s</p><span>%d registro(s) &rarr;</span></a>'
        % (l("/municipios/%s/" % m["id"]), esc(m["nome"]), esc(m["resumo"][:160] + "…"), num_registros_municipio(m["id"]))
        for m in MUNICIPIOS
    )
    conteudo = breadcrumb([("Início", "/"), ("Municípios", None)]) + (
        "<h1>Atuação por localidade</h1>"
        '<p class="lead">Páginas territoriais existem apenas onde há evidência real de atuação. A regional de Marília, '
        "dirigida por Walter Ihoshi a partir de 2023, atende 51 municípios — mas só têm página individual aqueles com "
        "registros documentados. Nenhuma página territorial vazia é criada.</p>"
        "<h2>Municípios com registros</h2>"
        '<div class="grade-grade">%s</div>' % cards
    )
    pagina("/municipios/", "Walter Ihoshi por município: ações, projetos e atuação",
           "Onde Walter Ihoshi atuou: páginas territoriais com registros documentados.",
           conteudo, [jsonld_colecao("Municípios", "Organização territorial do acervo.", "/municipios/")],
           trilha=[("Início", "/"), ("Municípios", "/municipios/")], sumario=False)

def pag_municipio(m):
    regs = [r for r in REALIZACOES if m["id"] in r["municipios"]]
    destaques = "".join("<li>%s</li>" % esc(d) for d in m["destaques"])
    conteudo = breadcrumb([("Início", "/"), ("Municípios", "/municipios/"), (m["nome"], None)]) + (
        "<h1>Walter Ihoshi em %s: ações, projetos e atuação</h1>"
        '<p class="lead">%s</p>'
        "<h2>Histórico de atuação</h2><ul class='marcas'>%s</ul>"
        "<h2>Registros do acervo</h2>%s"
        "<h2>Assuntos relacionados</h2><p>%s</p>"
        "%s"
    ) % (
        esc(m["nome"]), esc(m["resumo"]),
        destaques, lista_registros(regs),
        chip_temas(sorted({t for r in regs for t in r["temas"]})) or "—",
        sec_fontes(m["fontes"]),
    )
    pagina("/municipios/%s/" % m["id"],
           "Walter Ihoshi em %s: ações, projetos e atuação" % m["nome"],
           "Atuação documentada de Walter Ihoshi em %s: %s" % (m["nome"], m["resumo"][:140]),
           conteudo,
           [jsonld_colecao("Walter Ihoshi em %s" % m["nome"], m["resumo"], "/municipios/%s/" % m["id"]),
            jsonld_local(m["nome"])],
           trilha=[("Início", "/"), ("Municípios", "/municipios/"), (m["nome"], "/municipios/%s/" % m["id"])])

def pag_timeline():
    itens = []
    for ev in TIMELINE:
        link = ""
        if ev.get("realizacao") and ev["realizacao"] in R:
            link = '<a class="tl-link" href="%s">Ver registro com fontes &rarr;</a>' % l("/realizacoes/%s/" % ev["realizacao"])
        itens.append(
            '<li class="tl-item" data-ano="%s"><div class="tl-ano">%s</div><div class="tl-corpo"><h2>%s</h2>'
            "<p>%s</p>%s<p class='tl-fontes'>Fontes: %s</p></div></li>"
            % (esc(str(ev["ano"])), esc(str(ev["ano"])), esc(ev["titulo"]), esc(ev["texto"]), link,
               ", ".join(esc(F[f]["nome"]) for f in ev["fontes"] if f in F))
        )
    decadas = sorted({int(str(ev["ano"])[:4]) // 10 * 10 for ev in TIMELINE})
    botoes = ('<button type="button" class="chip" data-decada="" aria-pressed="true">'
              'Todas as décadas <span class="n">%d</span></button>') % len(TIMELINE)
    botoes += "".join(
        '<button type="button" class="chip" data-decada="%d" aria-pressed="false">%d <span class="n">%d</span></button>'
        % (d, d, sum(1 for ev in TIMELINE if int(str(ev["ano"])[:4]) // 10 * 10 == d))
        for d in decadas
    )
    conteudo = breadcrumb([("Início", "/"), ("Linha do tempo", None)]) + (
        "<h1>Linha do tempo — trajetória pública (1961–2026)</h1>"
        '<p class="lead">Marcos documentais da trajetória de Walter Shindi Iihoshi. Cada marco aponta para fontes e, '
        "quando existente, para a página de registro detalhada.</p>"
        '<div class="filtro-anos" id="filtro-anos" data-navegacao-secoes role="group" '
        'aria-label="Filtrar e saltar por década">%s</div>'
        '<p class="filtro-contagem" id="anos-contagem" role="status" aria-live="polite"></p>'
        '<ol class="timeline">%s</ol>' % (botoes, "".join(itens))
    )
    pagina("/linha-do-tempo/", "Linha do tempo: a trajetória de Walter Ihoshi (1961–2026)",
           "Histórico cronológico documentado: formação, comércio, ACSP, Jabaquara, três mandatos, Jucesp, convênios e candidatura 2026.",
           conteudo, [jsonld_colecao("Linha do tempo", "Trajetória cronológica documentada.", "/linha-do-tempo/")],
           trilha=[("Início", "/"), ("Linha do tempo", "/linha-do-tempo/")], sumario=False)

def pag_mandatos():
    tabela = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(c["cargo"]), esc(c["periodo"]), esc(c["partido"]))
        for c in PESSOA["cargos"]
    )
    elei = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (c["ano"], esc(c["partido"]), esc(c["resultado"]),
           ("%s votos" % format(c["votos"], ",d").replace(",", ".")) if c["votos"] else "—")
        for c in ELEICOES["candidaturas"]
    )
    migalha = breadcrumb([("Início", "/"), ("Mandatos", None)])
    conteudo = migalha + (
        "<h1>Atuação parlamentar na Câmara dos Deputados</h1>"
        '<p class="lead">Walter Ihoshi exerceu mandatos de deputado federal por São Paulo em três legislaturas. '
        "Nas de 2011 e 2015 entrou como suplente e foi efetivado ao longo da legislatura — este acervo diferencia "
        "eleição, suplência e exercício.</p>"
        "<h2>Legislaturas e exercício</h2>"
        + tabela_responsiva("Legislaturas, cargos e partidos",
                            ("Cargo", "Período", "Partido"), tabela) +
        "<h2>Como entrou em cada legislatura</h2>"
        "<ul class='marcas'>"
        "<li><strong>2007–2011 (53ª):</strong> eleito em 2006 pelo PFL com 101.097 votos; posse em 01/02/2007.</li>"
        "<li><strong>2011–2015 (54ª):</strong> suplente do DEM/PSD; assumiu em múltiplos períodos por licenças de "
        "Walter Feldman, Edson Aparecido, José Anibal e Arnaldo Jardim (registros oficiais de suplência da Câmara).</li>"
        "<li><strong>2015–2019 (55ª):</strong> suplente do PSD; assumiu por licença de Edinho Araújo (fev–out/2015) e "
        "foi efetivado em 01/01/2017, pela renúncia do titular, permanecendo até 31/01/2019.</li></ul>"
        "<h2>Proposições</h2>"
        "<p>Segundo a base de dados abertos da Câmara dos Deputados, Ihoshi apresentou mais de 500 proposições entre "
        "2007 e 2018 — entre projetos de lei, emendas constitucionais, requerimentos, indicações e pareceres. As "
        "peças com resultado normativo ou relevância documentada ganham página própria no acervo:</p>"
        "<ul class='marcas'>"
        "<li><a href='" + l("/realizacoes/ponte-hiroshi-sumida/") + "'>PL 2448/2007</a> — autoria; transformado na Lei nº 12.207/2010 (Ponte Comendador Hiroshi Sumida).</li>"
        "<li><a href='" + l("/realizacoes/cadastro-positivo/") + "'>PLP 441/2017</a> — relatoria; transformado na Lei Complementar nº 166/2019 (Novo Cadastro Positivo).</li>"
        "<li><a href='" + l("/realizacoes/indicacao-consulado-hamamatsu/") + "'>Indicação 31921/2008</a> — consulado brasileiro em Hamamatsu (Japão).</li>"
        "<li><a href='" + l("/realizacoes/requerimento-subcomissao-centenario/") + "'>Requerimento 4717/2007</a> — Subcomissão do Centenário da Imigração Japonesa.</li></ul>"
        "<p>Consulta integral: <a href='https://dadosabertos.camara.leg.br/api/v2/proposicoes?idDeputadoAutor=141560&amp;itens=100&amp;ordenarPor=id&amp;ordem=ASC' target='_blank' rel='noopener'>proposições de autoria na API de dados abertos da Câmara</a>.</p>"
        "<h2>Comissões</h2>"
        "<ul class='marcas'>"
        "<li><strong>Comissão de Defesa do Consumidor (CDC):</strong> titular em quase todos os períodos entre 2007 e "
        "2019; 2º vice-presidente (2008–2009) e 3º vice-presidente (2010). <a href='" + l("/realizacoes/atuacao-defesa-consumidor/") + "'>Registro detalhado</a>.</li>"
        "<li><strong>Comissões especiais:</strong> SuperSimples (PLP 25/2007), Código Comercial (PL 1572/11), Registro "
        "Civil Nacional, tributação de micro e pequenas empresas (PLP 420/2014), piso de vigilantes, reforma tributária "
        "(PEC 293/04) e Cadastro Positivo (relator).</li>"
        "<li><strong>Comissão externa (2011):</strong> entrada de produtos do Japão após Fukushima. "
        "<a href='" + l("/realizacoes/comissao-externa-produtos-japao/") + "'>Registro detalhado</a>.</li>"
        "<li><strong>Outras permanentes:</strong> Ciência, Tecnologia e Inovação; Desenvolvimento Econômico; "
        "Desenvolvimento Urbano; Trabalho; Relações Exteriores e de Defesa Nacional (suplente); Finanças e Tributação (suplente).</li></ul>"
        "<h2>Frentes parlamentares</h2>"
        "<p>A biografia oficial registra participação em frentes como a Mista da Micro e Pequena Empresa, Comércio "
        "Exterior, Combate à Pirataria, Direitos do Contribuinte, Santas Casas de Misericórdia e Segurança Pública.</p>"
        "<h2>Funções de liderança</h2>"
        "<p>Vice-líder da bancada do DEM (26/08/2010) e do PSD (03/05/2017). <a href='" + l("/realizacoes/vice-lider-bancadas/") + "'>Registro detalhado</a>.</p>"
        "<h2>Histórico eleitoral</h2>"
        + tabela_responsiva("Histórico eleitoral: ano, partido, resultado e votos",
                            ("Ano", "Partido", "Resultado", "Votos"), elei) +
        "<p class='nota-tabela'>" + esc(ELEICOES["nota_mandatos"]) + "</p>"
        "<h2>Votações nominais e discursos</h2>"
        "<p>Os sistemas oficiais da Casa registram votações nominais e discursos de cada parlamentar por legislatura. "
        "Este acervo não reproduz automaticamente essas bases; registros individuais são abertos quando há fonte "
        "específica verificável. Importante: nos dias das votações do impeachment da presidente Dilma Rousseff "
        "(abril e agosto de 2016), Walter Ihoshi não estava em exercício (havia se afastado em outubro de 2015 e só "
        "reassumiu em janeiro de 2017), razão pela qual este acervo não registra voto seu nesse episódio — divergindo "
        "de compilações que lhe atribuem participação.</p>"
    ) + sec_fontes(["camara-bio", "camara-api", "camara-ficha-plp441", "congressoemfoco-2006",
                    "plural-2026", "tse-divulga", "en-wikipedia"])
    pagina("/mandatos/", "Walter Ihoshi na Câmara dos Deputados: mandatos, comissões e proposições",
           "Atuação parlamentar de Walter Ihoshi: três legislaturas (2007–2019), comissões, frentes, proposições, "
           "relatoria do Novo Cadastro Positivo e histórico eleitoral.",
           conteudo, [jsonld_colecao("Mandatos", "Atuação parlamentar documentada.", "/mandatos/")],
           trilha=[("Início", "/"), ("Mandatos", "/mandatos/")])

def pag_jucesp():
    conteudo = breadcrumb([("Início", "/"), ("Jucesp", None)]) + (
        "<h1>Walter Ihoshi na Jucesp (2019–2023)</h1>"
        '<p class="lead">Presidiu a Junta Comercial do Estado de São Paulo entre fevereiro de 2019 e o início de 2023, '
        "período em que a autarquia digitalizou processos, aderiu ao Balcão Único nacional e registrou o recorde "
        "histórico de abertura de empresas no Estado (288.502 novos CNPJs em 2021).</p>"
        "<h2>Período e forma de investidura</h2>"
        "<ul class='marcas'>"
        "<li>Nomeado pelo governador João Dória (PSDB); publicação no Diário Oficial do Estado em 16/02/2019.</li>"
        "<li>Sucessão: registros institucionais de abril–maio de 2023 já se referem a Ihoshi como ex-presidente; "
        "a presidência passou a ser exercida por Paulo Henrique Schoueri.</li></ul>"
        "<h2>O que foi feito — separando os papéis</h2>"
        "<ul class='marcas'>"
        "<li><strong>Presidiu:</strong> a autarquia, respondendo pelo registro empresarial do Estado de São Paulo.</li>"
        "<li><strong>Coordenou/gestão:</strong> o programa de modernização — digitalização para abertura e fechamento "
        "de empresas, redução do uso de papel e integração com Receita Federal, Fazenda estadual e prefeituras.</li>"
        "<li><strong>Parceria (não autoria exclusiva):</strong> o Balcão Único, operante em São Paulo a partir de "
        "15/01/2021, foi criado em parceria entre Jucesp, governo federal e governo estadual.</li>"
        "<li><strong>Contexto dos números:</strong> o recorde de 2021 (288.502 aberturas, 28,4%% acima do recorde "
        "anterior de 2019) reflete também a retomada econômica pós-pandemia — reconhecimento feito pelo próprio "
        "presidente da autarquia à imprensa.</li></ul>"
        "<h2>Números públicos do período</h2>"
        "<ul class='marcas'>"
        "<li>2021: 288.502 novas empresas no Estado — maior número da série histórica iniciada em 1998 (fonte: Jucesp, "
        "via Diário do Comércio e Valor Econômico).</li>"
        "<li>A autarquia responde por cerca de 40%% das aberturas de empresas do Brasil, segundo dados que divulga.</li>"
        "<li>Agosto/2021–abril/2022: mais de 213 mil novas empresas, alta de 6,19%% sobre o período anterior (Jucesp).</li></ul>"
        "<h2>Registros do acervo</h2>%s"
        "<h2>Atuação paralela no período</h2>"
        "<p>Em 2020–2021, manteve interlocução com municípios da região de Marília e Assis, incluindo visitas sobre "
        "saúde e finanças municipais (ver <a href='%s'>Assis</a>).</p>"
        "%s"
    ) % (
        lista_registros([R["nomeacao-jucesp"], R["desburocratizacao-jucesp"]]),
        l("/municipios/assis/"),
        sec_fontes(["giromarilia-jucesp", "assiscity-jucesp", "visaonoticias-jucesp", "dcomercio-balcao-unico",
                    "dcomercio-recorde-2021", "valor-jucesp-2022", "crtsp-jucesp", "eparaguacu-jucesp",
                    "agenciadcnews-jucesp"]),
    )
    pagina("/jucesp/", "Walter Ihoshi na Jucesp: gestão, Balcão Único e recorde de abertura de empresas",
           "Atuação de Walter Ihoshi à frente da Junta Comercial do Estado de São Paulo (2019–2023), com números "
           "públicos, medidas de desburocratização e papéis claramente separados.",
           conteudo, [jsonld_colecao("Jucesp", "Dossiê da gestão na Jucesp.", "/jucesp/")],
           trilha=[("Início", "/"), ("Jucesp", "/jucesp/")])

def pag_convenios():
    conteudo = breadcrumb([("Início", "/"), ("Convênios", None)]) + (
        "<h1>Walter Ihoshi e os convênios do Governo de São Paulo (2023–2026)</h1>"
        '<p class="lead">Em setembro de 2023, foi nomeado pelo governador Tarcísio de Freitas e pelo secretário de '
        "Governo e Relações Institucionais, Gilberto Kassab, diretor do Escritório Regional de Marília — diretoria "
        "responsável por mediar convênios e demandas de 51 municípios do Centro-Oeste paulista junto ao Estado.</p>"
        "<h2>Como funciona o papel</h2>"
        "<ul class='marcas'>"
        "<li>A regional recebe demandas de prefeituras e articula a liberação de recursos estaduais.</li>"
        "<li><strong>A celebração dos convênios é ato do Governo do Estado e das prefeituras</strong> — o papel "
        "documentado de Ihoshi é de intermediação e articulação institucional.</li></ul>"
        "<h2>Convênios e valores</h2>"
        "<div class='alerta'>Transparência sobre os números: os valores de convênios para Marília divulgados na "
        "imprensa regional (quase R$ 15 milhões anunciados em abril/2024; R$ 36 milhões consolidados em publicações "
        "de período eleitoral de 2026) foram declarados pelo então diretor e pelas prefeituras envolvidas. Este "
        "acervo os registra como declarações — não como valores auditados — até a conferência documento a documento "
        "nos sistemas oficiais do Estado.</div>"
        "<ul class='marcas'>"
        "<li>Marília: convênios para recapeamento, ciclovia e Parque da Criança anunciados a partir de 2024.</li>"
        "<li>Assis: interlocução sobre crise financeira e saúde municipal (registros de 2020–2021, anteriores à "
        "diretoria).</li>"
        "<li>Suzano: visita institucional à Câmara Municipal em março de 2025.</li></ul>"
        "<h2>Registros do acervo</h2>%s"
        "<h2>Como conferir os convênios oficiais</h2>"
        "<p>Os convênios firmados entre o Estado de São Paulo e municípios podem ser consultados nos portais oficiais "
        "de transparência do Estado e das prefeituras. A rotina de atualização deste acervo (ver <a href='%s'>"
        "metodologia</a>) prevê a incorporação progressiva das referências documentais por convênio.</p>"
        "%s"
    ) % (
        l("/fontes/"),
        lista_registros([R["diretor-convenios-marilia"], R["convenios-marilia-2023-2026"], R["visita-suzano-2025"],
                         R["visita-assis-2021"]]),
        sec_fontes(["odiariodovale-convenios", "marilia-gov-regional", "psd-escritorio-marilia",
                    "marilianoticia-convenios-2024", "marilianoticia-36mi", "camara-suzano", "camara-assis"]),
    )
    pagina("/convenios/", "Walter Ihoshi e os convênios do Governo de São Paulo (2023–2026)",
           "Diretoria de convênios da regional de Marília: 51 municípios, articulação com prefeituras e valores "
           "declarados, com notas de evidência.",
           conteudo, [jsonld_colecao("Convênios", "Dossiê da atuação em convênios estaduais.", "/convenios/")],
           trilha=[("Início", "/"), ("Convênios", "/convenios/")])

def pag_nikkei():
    conteudo = breadcrumb([("Início", "/"), ("Comunidade nikkei", None)]) + (
        "<h1>Walter Ihoshi e a comunidade nipo-brasileira</h1>"
        '<p class="lead">Filho de imigrantes japoneses — o pai, Migaku Iihoshi, veio de Kumamoto; a mãe, Yoshiko, '
        "nasceu em Guaiçara (SP) —, Walter Ihoshi cresceu na Liberdade e construiu ao longo da carreira pública uma "
        "ponte entre o poder público e as entidades da comunidade nikkei.</p>"
        "<h2>Entidades e espaços</h2>"
        "<ul class='marcas'>"
        "<li><strong>Bunkyo</strong> (Sociedade Brasileira de Cultura Japonesa e Assistência Social): participação em "
        "sessões solenes e, em 2025, coordenação da homenagem a políticos nipo-brasileiros eleitos em 2024.</li>"
        "<li><strong>Nikkey Clube de Marília</strong>: participação anual no Japan Fest; apontado pela imprensa "
        "especializada como um dos responsáveis pela visita da Princesa Mako à cidade em 2018.</li>"
        "<li><strong>Câmara de Comércio e Indústria Japonesa do Brasil:</strong> membro da Comissão de Assuntos "
        "Trabalhistas ainda na fase empresarial (registro biográfico oficial).</li></ul>"
        "<h2>Atuação parlamentar com a comunidade</h2>"
        "<ul class='marcas'>"
        "<li>Requerimento pela Subcomissão do Centenário da Imigração Japonesa (2007) e co-autoria do requerimento da "
        "sessão solene dos 100 anos (2008).</li>"
        "<li>Lei nº 12.207/2010, de sua autoria, denominando Ponte Comendador Hiroshi Sumida, em Registro (SP), em "
        "homenagem a um líder nikkei da região do Vale do Ribeira.</li>"
        "<li>Indicação ao Itamaraty pela criação de consulado brasileiro em Hamamatsu (2008), cidade com grande "
        "comunidade brasileira no Japão.</li>"
        "<li>Sessão solene dos 107 anos da imigração na Alesp (2015) e centenário da Colônia Hirano em Cafelândia (2015).</li></ul>"
        "<h2>Registros do acervo</h2>%s"
        "%s"
    ) % (
        lista_registros([R["ponte-hiroshi-sumida"], R["requerimento-subcomissao-centenario"],
                         R["sessao-solene-centenario-2008"], R["indicacao-consulado-hamamatsu"],
                         R["sessao-107-anos-imigracao-alesp"], R["colonia-hirano-100-anos"],
                         R["japan-fest-marilia"], R["visita-princesa-mako-marilia"], R["homenagem-bunkyo-2025"]]),
        sec_fontes(["camara-news-sessao-centenario", "camara-api", "lei-12207", "alesp-107-anos",
                    "alesp-okinawa-110-anos", "bunkyo-2025", "bunkyo-hirano", "bunkyo-2015", "nipponja-japan-fest"]),
    )
    pagina("/comunidade-nikkei/", "Walter Ihoshi e a comunidade nipo-brasileira: entidades, eventos e relações Brasil–Japão",
           "Relação histórica documentada de Walter Ihoshi com a comunidade nipo-brasileira: Bunkyo, Japan Fest, "
           "centenário da imigração, lei da Ponte Hiroshi Sumida e intercâmbio Brasil–Japão.",
           conteudo, [jsonld_colecao("Comunidade nikkei", "Dossiê da relação com a comunidade nipo-brasileira.", "/comunidade-nikkei/")],
           trilha=[("Início", "/"), ("Comunidade nikkei", "/comunidade-nikkei/")])

def pag_fontes():
    niveis = "".join(
        "<tr><td><strong>%s</strong> (%s)</td><td>%s</td></tr>" % (n["valor"], esc(n["rotulo"]), esc(n["descricao"]))
        for n in FONTES["niveis"]
    )
    fontes_html = "".join(
        '<div class="fonte-item"><a href="%s" target="_blank" rel="noopener nofollow">%s</a>'
        '<span class="fonte-meta">%s &middot; evidência %s &middot; consultada em %s</span>%s</div>'
        % (esc(f["url"]), esc(f["nome"]), esc(f["tipo"]), f["nivel"], fmt_data(f.get("consultada_em", "")),
           ('<span class="fonte-nota">%s</span>' % esc(f["nota"])) if f.get("nota") else "")
        for f in sorted(FONTES["fontes"], key=lambda x: -x["nivel"])
    )
    autor = CFG.get("autor", {})
    resp_nome = esc(autor.get("responsavel", ""))
    resp_site = esc(autor.get("site", ""))
    resp_site_limpo = esc(autor.get("site", "").replace("https://", "").replace("http://", "").rstrip("/"))
    migalha = breadcrumb([("Início", "/"), ("Fontes e método", None)])
    conteudo = migalha + (
        "<h1>Fontes, metodologia e critérios</h1>"
        '<p class="lead">Este acervo segue a lógica <strong>fato → evidência → contexto → território → tema → fonte</strong>. '
        "Nenhuma realização é publicada sem fonte verificável; nada é criado por inferência.</p>"
        "<h2>O que este site é — e o que não é</h2>"
        "<p>É um acervo público, independente e verificável da atuação de Walter Ihoshi, construído para pesquisa, "
        "citação e compartilhamento. Não é site institucional de campanha: propostas eleitorais não são apresentadas "
        "como realizações, e a página de cada registro distingue o papel exercido.</p>"
        "<h2>Como as fontes são selecionadas</h2>"
        "<p>Prioridade para: Câmara dos Deputados (incluindo a API de dados abertos), Governo e Diário Oficial do "
        "Estado de São Paulo, Jucesp, Diário Oficial da União, prefeituras e câmaras municipais, tribunais eleitorais, "
        "entidades oficiais e imprensa profissional. Publicações do próprio interessado valem como registro de "
        "posicionamento ou proposta — nunca como prova de realização.</p>"
        "<h2>Níveis de evidência</h2>"
        + tabela_responsiva("Escala de níveis de evidência e critérios", ("Escala", "Critério"), niveis) +
        "<p>Registros com evidência abaixo de 60 não são publicados como fato. Registros entre 60 e 69 (valores "
        "declarados em entrevistas ou publicações de período eleitoral) são marcados com nota de evidência visível.</p>"
        "<h2>Tipos de atuação</h2>"
        "<p>Cada registro classifica o papel: <em>autoria, relatoria, voto, articulação, gestão, convênio, projeto, "
        "lei, emenda, evento, reunião, posicionamento, proposta, entrevista, ação institucional</em>. Participação não "
        "vira autoria; apoio não vira realização individual; promessa não vira entrega.</p>"
        "<h2>Diferença entre proposta e realização</h2>"
        "<p>Proposta é qualquer matéria apresentada ou defendida (tramitando ou não). Realização exige resultado "
        "documentado — norma publicada, recurso executado, ato administrativo registrado.</p>"
        "<h2>Correções e atualizações</h2>"
        "<p>O acervo é atualizado com rotina de monitoramento contínua (coleta → deduplicação → extração de entidades "
        "→ classificação por tema e território → identificação do tipo de atuação → validação de evidência → "
        "publicação). Correções podem ser solicitadas pelo contato indicado no rodapé; alterações ficam registradas no "
        "histórico do repositório público do projeto e na página de <a href='" + l("/atualizacoes/") + "'>atualizações</a>.</p>"
        "<p>Última atualização desta versão: <strong>" + fmt_data(HOJE) + "</strong>.</p>"
        "<h2 id='eleitoral'>Nota de natureza eleitoral</h2>"
        "<p>Este site foi publicado no período eleitoral de 2026, ano em que Walter Ihoshi é candidato a deputado "
        "federal por São Paulo (PSD, nº 5599). Para cumprir as regras eleitorais aplicáveis: (i) o responsável pela "
        "publicação está identificado no rodapé de todas as páginas; (ii) o acervo não impulsiona conteúdo nem "
        "contrata publicidade; (iii) realizações históricas estão separadas de propostas de campanha; (iv) registros "
        "com fontes de período eleitoral têm nota de evidência explícita; (v) nenhum conteúdo sintético enganoso é "
        "utilizado. Responsável pela publicação deste site: <strong>" + resp_nome + "</strong> "
        "(<a href='" + resp_site + "' target='_blank' rel='noopener'>" + resp_site_limpo + "</a>).</p>"
        "<h2>Clipping diário</h2>"
        "<p>A página de <a href='" + l("/clipping/") + "'>clipping</a> reúne, com atualização automática (duas coletas "
        "por dia), todas as menções a Walter Ihoshi localizadas na imprensa e em fontes oficiais, com link para o "
        "original. Menções são publicadas como menções — a existência da matéria é o fato documentado. Apenas itens "
        "validados curatorialmente são promovidos a registros do acervo, com tipo de atuação e nível de evidência.</p>"
        "<h2>Registro de fontes consultadas</h2>"
        "<p class='lead'>" + str(len(FONTES["fontes"])) + " fontes catalogadas nesta versão:</p>"
        "<div class='lista-fontes'>" + fontes_html + "</div>"
    )
    pagina("/fontes/", "Fontes e metodologia — como este acervo é construído",
           "Metodologia do acervo: seleção de fontes, níveis de evidência, tipos de atuação, diferença entre "
           "proposta e realização, clipping diário, correções e nota de natureza eleitoral.",
           conteudo, [jsonld_colecao("Fontes e metodologia", "Critérios do acervo.", "/fontes/")],
           trilha=[("Início", "/"), ("Fontes e método", "/fontes/")])

def pag_atualizacoes():
    itens = "".join(
        '<li class="upd"><time>%s</time><div><h2>%s</h2><p>%s</p>'
        "<p class='upd-meta'>Tema: %s &middot; Município: %s</p>%s</div></li>"
        % (
            fmt_data(up["data"]), esc(up["titulo"]), esc(up["texto"]),
            esc(T[up["tema"]]["nome"]) if up.get("tema") and up["tema"] in T else "—",
            esc(M[up["municipio"]]["nome"]) if up.get("municipio") and up["municipio"] in M else "—",
            "".join('<a class="chip" href="%s">%s</a>' % (l("/realizacoes/%s/" % rid), esc(R[rid]["titulo"]))
                    for rid in up.get("registros", []) if rid in R),
        )
        for up in sorted(ATUALIZACOES, key=lambda x: x["data"], reverse=True)
    )
    migalha = breadcrumb([("Início", "/"), ("Atualizações", None)])
    conteudo = migalha + (
        "<h1>Últimas atualizações do acervo</h1>"
        '<p class="lead">Não é um portal de notícias: esta página registra apenas novos registros incorporados ao '
        "acervo, com fonte, tema e município.</p>"
        "<ul class='atualizacoes atualizacoes-pagina'>" + itens + "</ul>"
    )
    pagina("/atualizacoes/", "Atualizações do acervo — novos registros incorporados",
           "Novos registros incorporados ao acervo de Walter Ihoshi, com fontes, temas e municípios.",
           conteudo, [jsonld_colecao("Atualizações", "Registro de incorporações ao acervo.", "/atualizacoes/")],
           trilha=[("Início", "/"), ("Atualizações", "/atualizacoes/")], sumario=False)

# ---------------------------------------------------------------- clipping
def pag_clipping():
    itens = sorted(CLIPPING, key=lambda x: (x.get("data", ""), x.get("titulo", "")), reverse=True)
    if itens:
        dias = []
        por_dia = {}
        for c in itens:
            d = (c.get("data") or "")[:10]
            if d not in por_dia:
                dias.append(d)
            por_dia.setdefault(d, []).append(c)
        dias.sort(reverse=True)
        navegadores = []
        ontem_iso = str(date.fromordinal(date.today().toordinal() - 1))
        blocos = []
        for d in dias:
            if d == HOJE:
                rotulo = "Hoje (%s)" % fmt_data(d)
            elif d == ontem_iso:
                rotulo = "Ontem (%s)" % fmt_data(d)
            else:
                rotulo = fmt_data(d)
            linhas = "".join(
                '<li class="clip-item" data-fonte="%s" data-oficial="%d" data-texto="%s">'
                '<div class="clip-esq">%s</div>'
                '<div><a href="%s" target="_blank" rel="noopener nofollow">%s</a>'
                "<p class='clip-meta'>%s &middot; nível da fonte: %s%s%s</p></div></li>"
                % (
                    esc(c.get("fonte", "")),
                    1 if int(c.get("fonte_nivel", 0) or 0) >= 80 else 0,
                    esc(("%s %s %s" % (c["titulo"], c.get("fonte", ""), c.get("data", ""))).lower()),
                    badge_evidencia(min(c.get("fonte_nivel", 60), 100)),
                    esc(c["link"]), esc(c["titulo"]), esc(c.get("fonte", "")),
                    c.get("fonte_nivel", "—"),
                    (" &middot; " + esc(T[c["tema_proposto"]]["nome"])) if c.get("tema_proposto") and c["tema_proposto"] in T else "",
                    (" &middot; " + esc(M[c["municipio_proposto"]]["nome"])) if c.get("municipio_proposto") and c["municipio_proposto"] in M else "",
                )
                for c in por_dia[d]
            )
            blocos.append("<section class='clip-dia' id='dia-%s'><h2>%s <span class='conta'>(%d)</span></h2><ul class='clip-lista'>%s</ul></section>"
                          % (esc(d), esc(rotulo), len(por_dia[d]), linhas))
            navegadores.append('<a class="chip" href="#dia-%s">%s <span class="conta-mini">%d</span></a>'
                               % (esc(d), esc(rotulo.split(" (")[0]), len(por_dia[d])))
        corpo = (('<nav class="filtro-anos" data-navegacao-secoes aria-label="Ir para um dia">'
                  "%s</nav>") % "".join(navegadores)) if len(navegadores) > 1 else ""
        corpo += "".join(blocos)
        atualizado = ("Última coleta: <strong>%s</strong>." % esc(str(CLIPPING_ATUALIZADO_EM)[:10].replace("-", "/"))) if CLIPPING_ATUALIZADO_EM else ""
    else:
        corpo = ("<p class='lead'>Ainda não há menções coletadas. A rotina diária de monitoramento (duas execuções "
                 "por dia) alimenta automaticamente esta página com tudo o que a imprensa e as fontes oficiais "
                 "publicarem sobre Walter Ihoshi.</p>")
        atualizado = ""
    migalha = breadcrumb([("Início", "/"), ("Clipping", None)])
    painel_clip = ""
    if itens:
        painel_clip = (
            '<form class="filtros" id="filtros-clipping" aria-label="Filtrar menções">'
            '<div class="filtros-linha">'
            '<div class="campo"><label for="clip-texto">Filtrar por texto ou veículo</label>'
            '<input id="clip-texto" type="search" autocomplete="off" placeholder="Título da matéria, jornal, cidade…"></div>'
            '<div class="campo"><label for="clip-oficiais">Tipo de fonte</label>'
            '<label class="chip-opcao" style="margin-top:4px">'
            '<input type="checkbox" id="clip-oficiais"><span>Somente fontes oficiais/institucionais (80+)</span></label>'
            '</div></div>'
            '<div class="filtros-rodape">'
            '<p class="filtro-contagem" id="clip-contagem" role="status" aria-live="polite"></p>'
            "</div></form>"
            + estado_vazio(
                "Nenhuma menção com esse filtro",
                "Nenhuma menção coletada corresponde ao filtro escolhido. Fontes oficiais e institucionais "
                "só entram no clipping quando a coleta diária as encontra — a ausência aqui é ausência de "
                "menção, não de atuação.",
            ).replace('class="estado estado-vazio"', 'class="estado estado-vazio" id="clip-aviso" hidden', 1)
        )
    conteudo = migalha + (
        "<h1>Clipping do dia — menções a Walter Ihoshi</h1>"
        '<p class="lead">Monitoramento diário e automático do nome <strong>Walter Ihoshi / Walter Iihoshi</strong> '
        "na imprensa e em fontes oficiais. Cada menção leva ao veículo original.</p>"
        "<div class='alerta'><strong>Como ler esta página:</strong> o clipping registra menções — a existência da "
        "matéria é o fato documentado. Ele não equivale aos <a href='%s'>registros verificados do acervo</a>: menções "
        "com conteúdo relevante são validadas (fonte, tipo de atuação, resultado) e promovidas a registros com nível "
        "de evidência.</div>%s" % (l("/realizacoes/"), atualizado)
    ) + painel_clip + corpo
    pagina("/clipping/", "Clipping do dia: o que a imprensa publica sobre Walter Ihoshi",
           "Monitoramento diário de menções a Walter Ihoshi (Walter Iihoshi) na imprensa e em fontes oficiais, "
           "com link para cada matéria e separação clara entre menção e registro verificado.",
           conteudo,
           [jsonld_colecao("Clipping diário", "Menções a Walter Ihoshi coletadas automaticamente.", "/clipping/")],
           trilha=[("Início", "/"), ("Clipping", "/clipping/")], sumario=False)


# ---------------------------------------------------------------- busca
def montar_indice_busca():
    itens = []
    for r in REALIZACOES:
        itens.append({
            "t": r["titulo"], "d": r["resumo"], "u": l("/realizacoes/%s/" % r["id"]),
            "cat": "Realização — %s" % tipo_rotulo(r["tipo"]),
            "ch": " ".join([r["titulo"], r["resumo"], r.get("tipo_detalhe", ""), r["periodo"], r["cargo"]]
                           + [T[t]["nome"] for t in r["temas"] if t in T]
                           + [M[m]["nome"] for m in r["municipios"] if m in M]
                           + r.get("entidades", [])
                           + (["cadastro positivo", "JUCESP", "jucesp"] if "jucesp" in json.dumps(r) else [])),
        })
    for t in TEMAS:
        itens.append({"t": "Tema: %s" % t["nome"], "d": t["resumo"], "u": l("/temas/%s/" % t["id"]),
                      "cat": "Tema", "ch": " ".join([t["nome"], t["resumo"]])})
    for m in MUNICIPIOS:
        itens.append({"t": "Walter Ihoshi em %s" % m["nome"], "d": m["resumo"], "u": l("/municipios/%s/" % m["id"]),
                      "cat": "Município", "ch": " ".join([m["nome"], m["regiao"], m["resumo"]] + m["destaques"])})
    for titulo, desc, caminho in [
        ("Atuação parlamentar na Câmara dos Deputados", "mandatos, comissões, proposições", "/mandatos/"),
        ("Walter Ihoshi na Jucesp", "gestão 2019–2023, Balcão Único, recorde de aberturas", "/jucesp/"),
        ("Convênios do Governo de São Paulo", "diretoria regional de Marília, 51 municípios", "/convenios/"),
        ("Comunidade nipo-brasileira", "Bunkyo, Japan Fest, centenários, Brasil–Japão", "/comunidade-nikkei/"),
        ("Linha do tempo 1961–2026", "trajetória completa documentada", "/linha-do-tempo/"),
        ("Fontes e metodologia", "critérios, níveis de evidência", "/fontes/"),
    ]:
        itens.append({"t": titulo, "d": desc, "u": l(caminho), "cat": "Página do acervo", "ch": titulo + " " + desc})
    for ev in TIMELINE:
        itens.append({"t": "%s — %s" % (ev["ano"], ev["titulo"]), "d": ev["texto"],
                      "u": l("/linha-do-tempo/"), "cat": "Linha do tempo",
                      "ch": "%s %s %s" % (ev["ano"], ev["titulo"], ev["texto"])})
    for c in CLIPPING[:40]:
        itens.append({"t": c["titulo"], "d": "Menção em %s (%s)" % (c.get("fonte", ""), fmt_data(c.get("data"))),
                      "u": l("/clipping/"), "cat": "Clipping",
                      "ch": "%s %s" % (c["titulo"], c.get("fonte", ""))})
    return itens

def indice_sem_js():
    """Rota de fuga quando não há JavaScript: o índice curado do acervo,
    renderizado no build. Buscar é conveniência; encontrar é obrigação."""
    blocos = []
    blocos.append("<div><p class=\"rodape-titulo\">Dossiês</p><ul>%s</ul></div>" % "".join(
        '<li><a href="%s">%s</a></li>' % (l(c), esc(r))
        for c, r in [("/mandatos/", "Mandatos na Câmara dos Deputados"),
                     ("/jucesp/", "Presidência da Jucesp (2019–2023)"),
                     ("/convenios/", "Convênios do Governo de São Paulo"),
                     ("/comunidade-nikkei/", "Comunidade nipo-brasileira"),
                     ("/linha-do-tempo/", "Linha do tempo 1961–2026")]))
    blocos.append("<div><p class=\"rodape-titulo\">Temas</p><ul>%s</ul></div>" % "".join(
        '<li><a href="%s">%s</a> <span class="conta-mini">%d</span></li>'
        % (l("/temas/%s/" % t["id"]), esc(t["nome"]), num_registros_tema(t["id"]))
        for t in sorted(TEMAS, key=lambda x: x["nome"])))
    blocos.append("<div><p class=\"rodape-titulo\">Municípios</p><ul>%s</ul></div>" % "".join(
        '<li><a href="%s">%s</a> <span class="conta-mini">%d</span></li>'
        % (l("/municipios/%s/" % m["id"]), esc(m["nome"]), num_registros_municipio(m["id"]))
        for m in sorted(MUNICIPIOS, key=lambda x: x["nome"])))
    return '<div class="rodape-grade">%s</div>' % "".join(blocos)

def pag_busca():
    itens = montar_indice_busca()
    dados_json = json.dumps(itens, ensure_ascii=False).replace("</", "<\\/")
    conteudo = (
        breadcrumb([("Início", "/"), ("Busca", None)]) +
        "<h1>Busca no acervo</h1>"
        '<p class="lead">Pesquise realizações, municípios, temas, cargos, proposições e marcos da linha do tempo. '
        "O índice cobre <strong>%d itens</strong> desta versão do acervo.</p>"
        '<p class="dica">Atalhos: pressione <kbd>/</kbd> ou <kbd>Ctrl</kbd>+<kbd>K</kbd> em qualquer página para '
        "vir direto para cá; use <kbd>↑</kbd> <kbd>↓</kbd> para percorrer os resultados e <kbd>Esc</kbd> para limpar.</p>"
        '<form class="busca-pagina" role="search" action="%s" method="get">'
        '<label class="sr-only" for="campo-busca">Buscar no acervo</label>'
        '<div class="campo-busca-grande">'
        '<input id="campo-busca" name="q" type="search" autocomplete="off" '
        'placeholder="Pesquise por município, projeto, lei ou assunto">'
        '<button type="button" class="busca-limpar" id="limpar-busca" aria-label="Limpar a busca">'
        '<span aria-hidden="true">✕</span></button></div>'
        '<noscript><button type="submit" class="btn">Buscar</button></noscript>'
        "</form>"
        '<p class="busca-atalhos" id="buscas-recentes" hidden></p>'
        '<p class="conta-resultados" id="conta-resultados" role="status" aria-live="polite"></p>'
        '<div id="resultados"></div>'
        "<noscript>"
        + estado_vazio(
            "A busca instantânea precisa de JavaScript",
            "Sem JavaScript o campo acima não filtra em tempo real. Todo o conteúdo continua acessível "
            "pelos índices abaixo — nada deste site fica atrás do script.",
        ) + indice_sem_js() + "</noscript>"
        '<script type="application/json" id="dados-busca">%s</script>'
    ) % (len(itens), l("/busca/"), dados_json)
    pagina("/busca/", "Busca no acervo de Walter Ihoshi",
           "Pesquise por município, projeto ou assunto na trajetória documentada de Walter Ihoshi.",
           conteudo, [jsonld_colecao("Busca", "Busca no acervo.", "/busca/")],
           trilha=[("Início", "/"), ("Busca", "/busca/")], sumario=False)

# ---------------------------------------------------------------- feeds e índices
def gerar_sitemap(paginas):
    urls = "".join(
        "<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>"
        % (u(p), HOJE, freq, prio)
        for p, freq, prio in paginas
    )
    with open(os.path.join(SAIDA, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % urls)

def gerar_robots():
    with open(os.path.join(SAIDA, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: %s\n" % u("/sitemap.xml"))

def gerar_feed():
    itens_acervo = "".join(
        "<item><title>%s</title><link>%s</link><guid>%s</guid><pubDate>%s</pubDate><description>%s</description></item>"
        % (esc(up["titulo"]), u("/atualizacoes/"), u("/atualizacoes/") + "#" + up["data"], up["data"], esc(up["texto"]))
        for up in sorted(ATUALIZACOES, key=lambda x: x["data"], reverse=True)
    )
    itens_clip = "".join(
        "<item><title>[Clipping] %s</title><link>%s</link><guid>%s</guid><pubDate>%s</pubDate><description>Menção em %s</description></item>"
        % (esc(c["titulo"]), esc(c["link"]), esc(c["link"]), c.get("data", HOJE), esc(c.get("fonte", "")))
        for c in sorted(CLIPPING, key=lambda x: x.get("data", ""), reverse=True)[:10]
    )
    itens = itens_acervo + itens_clip
    with open(os.path.join(SAIDA, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
            "<title>%s</title><link>%s</link><description>%s</description><language>pt-BR</language>%s</channel></rss>"
            % (esc(CFG["nome_projeto"]), u("/"), esc(CFG["descricao"]), itens)
        )

def gerar_indice_json():
    with open(os.path.join(SAIDA, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(montar_indice_busca(), f, ensure_ascii=False)

# ---------------------------------------------------------------- 404
def pag_404():
    """Erro 404 como página de recuperação: explica, oferece busca e dá
    saída para as seções principais. Nunca um beco sem saída."""
    contagens = contagens_nav()
    atalhos = "".join(
        '<a class="btn btn-fantasma" href="%s">%s <span class="conta">%s</span></a>'
        % (l(c), esc(r), esc(contagens.get(c, "")))
        for c, r in [("/realizacoes/", "Realizações"), ("/temas/", "Temas"),
                     ("/municipios/", "Municípios"), ("/linha-do-tempo/", "Linha do tempo"),
                     ("/fontes/", "Fontes e método")]
    )
    conteudo = (
        '<h1>Página não encontrada</h1>'
        '<p class="lead">O endereço acessado não existe neste acervo. Isso acontece quando um registro é '
        "renomeado, quando o link foi copiado pela metade, ou quando a página simplesmente nunca existiu.</p>"
        '<div class="estado estado-erro">'
        '<p class="estado-titulo">Como recuperar o que você procurava</p>'
        "<p>Nada foi publicado aqui sem fonte, e nada foi removido sem deixar rastro: o histórico completo "
        "de alterações do acervo é público no repositório do projeto.</p>"
        '<div class="estado-acoes"><a class="btn btn-ouro" href="%s">Buscar no acervo</a>%s</div>'
        "</div>"
        '<p class="dica">Se você chegou aqui por um link de outro site, avise o responsável pela publicação '
        "(endereço no rodapé) para que a referência seja corrigida.</p>"
        % (l("/busca/"), atalhos)
    )
    pagina("/404.html", "Página não encontrada — Acervo de Walter Ihoshi",
           "O endereço acessado não existe no acervo de atuação pública de Walter Ihoshi. "
           "Use a busca ou navegue pelas seções.",
           conteudo, [], sumario=False)

# ---------------------------------------------------------------- main
def main():
    if os.path.isdir(SAIDA):
        shutil.rmtree(SAIDA)
    os.makedirs(SAIDA)
    if os.path.isdir(STATIC):
        shutil.copytree(STATIC, os.path.join(SAIDA, "static"))

    pag_home()
    pag_realizacoes_lista()
    for r in REALIZACOES:
        pag_realizacao(r)
    pag_temas_lista()
    for t in TEMAS:
        pag_tema(t)
    pag_municipios_lista()
    for m in MUNICIPIOS:
        pag_municipio(m)
    pag_timeline()
    pag_mandatos()
    pag_jucesp()
    pag_convenios()
    pag_nikkei()
    pag_fontes()
    pag_atualizacoes()
    pag_clipping()
    pag_busca()
    pag_404()

    paginas = [("/", "daily", "1.0"), ("/realizacoes/", "weekly", "0.9"), ("/temas/", "weekly", "0.8"),
               ("/municipios/", "weekly", "0.8"), ("/linha-do-tempo/", "monthly", "0.8"),
               ("/mandatos/", "monthly", "0.9"), ("/jucesp/", "monthly", "0.9"), ("/convenios/", "weekly", "0.8"),
               ("/comunidade-nikkei/", "monthly", "0.8"), ("/clipping/", "daily", "0.8"),
               ("/fontes/", "monthly", "0.6"),
               ("/atualizacoes/", "daily", "0.7"), ("/busca/", "weekly", "0.5")]
    paginas += [("/realizacoes/%s/" % r["id"], "monthly", "0.8") for r in REALIZACOES]
    paginas += [("/temas/%s/" % t["id"], "monthly", "0.7") for t in TEMAS]
    paginas += [("/municipios/%s/" % m["id"], "monthly", "0.7") for m in MUNICIPIOS]
    gerar_sitemap(paginas)
    gerar_robots()
    gerar_feed()
    gerar_indice_json()

    total = sum(len(fs) for _, _, fs in os.walk(SAIDA))
    print("Site gerado em public/ — %d arquivos." % total)

if __name__ == "__main__":
    main()
