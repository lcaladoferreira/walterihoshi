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
NAV = [
    ("/realizacoes/", "Realizações"),
    ("/temas/", "Temas"),
    ("/municipios/", "Municípios"),
    ("/linha-do-tempo/", "Linha do tempo"),
    ("/mandatos/", "Mandatos"),
    ("/jucesp/", "Jucesp"),
    ("/convenios/", "Convênios"),
    ("/comunidade-nikkei/", "Comunidade nikkei"),
    ("/clipping/", "Clipping do dia"),
    ("/fontes/", "Fontes e método"),
]

def cabecalho(atual):
    itens = []
    for caminho, rotulo in NAV:
        classe = ' class="ativo"' if caminho == atual else ""
        itens.append('<a href="%s"%s>%s</a>' % (l(caminho), classe, rotulo))
    return (
        '<header class="topo">'
        '<div class="container">'
        '<a class="marca" href="%s"><span class="marca-nome">WALTER IHOSHI</span>'
        '<span class="marca-sub">Acervo de Atuação Pública</span></a>'
        '<form class="busca-topo" action="%s" method="get">'
        '<input type="search" name="q" placeholder="Pesquise por município, projeto ou assunto" aria-label="Pesquisar no acervo">'
        '<button type="submit">Pesquisar</button></form>'
        '<nav aria-label="Navegação principal">%s</nav>'
        "</div></header>" % (l("/"), l("/busca/"), "".join(itens))
    )

def rodape():
    return (
        '<footer class="rodape"><div class="container">'
        "<p><strong>%s</strong> — %s</p>"
        "<p>%s</p>"
        '<p class="rodape-links"><a href="%s">Realizações</a> &middot; <a href="%s">Linha do tempo</a> '
        '&middot; <a href="%s">Fontes e metodologia</a> &middot; <a href="%s">Últimas atualizações</a> '
        '&middot; <a href="%s">Clipping</a> &middot; <a href="%s">Busca</a> &middot; '
        '<a href="%s" target="_blank" rel="noopener">Feed RSS</a></p>'
        '<p class="rodape-resp">%s</p>'
        "<p>Atualizado em %s &middot; Dados e código auditáveis no repositório.</p>"
        "</div></footer>" % (
            esc(CFG["nome_projeto"]), esc(CFG["tagline"]),
            esc(CFG["descricao"]),
            l("/realizacoes/"), l("/linha-do-tempo/"), l("/fontes/"), l("/atualizacoes/"),
            l("/clipping/"), l("/busca/"), l("/feed.xml"),
            rodape_responsavel(),
            fmt_data(HOJE),
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

def pagina(caminho, titulo, descricao, conteudo, jsonld, og_tipo="website", trilha=None):
    """Monta e grava uma página HTML."""
    if trilha:
        jsonld = list(jsonld) + [jsonld_trilha(trilha)]
    html_doc = (
        "<!DOCTYPE html>\n"
        '<html lang="pt-BR">\n<head>\n'
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
        "%s\n</head>\n<body>\n%s\n<main id=\"conteudo\">%s</main>\n%s\n</body>\n</html>"
    ) % (
        esc(titulo), esc(descricao), u(caminho), og_tipo,
        esc(CFG["nome_projeto"]), esc(titulo), esc(descricao), u(caminho),
        u("/static/og.png"), l("/static/estilo.css"),
        esc(CFG["nome_projeto"]), l("/feed.xml"),
        l("/static/favicon.svg"),
        bloco_jsonld(jsonld),
        cabecalho(caminho if caminho != "/" else "/"),
        conteudo, rodape(),
    )
    destino = os.path.join(SAIDA, caminho.lstrip("/"), "index.html") if caminho != "/" else os.path.join(SAIDA, "index.html")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html_doc)

def card_registro(r):
    return (
        '<article class="card">'
        '<div class="card-tags"><span class="tag-tipo">%s</span>%s</div>'
        '<h3><a href="%s">%s</a></h3>'
        "<p>%s</p>"
        '<p class="card-meta">%s%s</p>'
        '<a class="card-link" href="%s">Ver registro completo com fontes &rarr;</a>'
        "</article>"
        % (
            esc(tipo_rotulo(r["tipo"])), badge_evidencia(r["evidence_score"]),
            l("/realizacoes/%s/" % r["id"]), esc(r["titulo"]),
            esc(r["resumo"]),
            chip_temas(r["temas"]), chip_municipios(r["municipios"]),
            l("/realizacoes/%s/" % r["id"]),
        )
    )

def lista_registros(registros, vazio="Nenhum registro nesta coleção."):
    cards = "".join(card_registro(r) for r in registros)
    return '<div class="grade">%s</div>' % cards if cards else "<p>%s</p>" % esc(vazio)

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
        "<p>Explore projetos, ações, realizações, mandatos, municípios e documentos que registram a atuação pública de "
        "<strong>Walter Shindi Iihoshi</strong> — três mandatos na Câmara dos Deputados (2007–2019), presidência da "
        "Jucesp (2019–2023) e diretoria de convênios do Governo de São Paulo (2023–2026).</p>"
        '<form class="busca-destaque" action="%s" method="get">'
        '<input type="search" name="q" placeholder="Pesquise por município, projeto ou assunto" aria-label="Pesquisar no acervo">'
        "<button type='submit'>Pesquisar no acervo</button></form>"
        '<p class="hero-exemplos">Experimente: '
        '<a href="%s">JUCESP</a> &middot; <a href="%s">Cadastro Positivo</a> &middot; '
        '<a href="%s">Marília</a> &middot; <a href="%s">microempresas</a> &middot; '
        '<a href="%s">Japão</a> &middot; <a href="%s">desburocratização</a></p>'
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
           conteudo, [jsonld_person(), jsonld_website()], og_tipo="profile")

def num_registros_tema(tid):
    return sum(1 for r in REALIZACOES if tid in r["temas"])

def num_registros_municipio(mid):
    return sum(1 for r in REALIZACOES if mid in r["municipios"])

def pag_realizacoes_lista():
    grupos = {}
    for r in REALIZACOES:
        grupos.setdefault(r["tipo"], []).append(r)
    ordem_tipos = ["LEI", "RELATORIA", "EMENDA", "GESTÃO", "ARTICULAÇÃO", "CONVÊNIO", "AÇÃO INSTITUCIONAL",
                   "PROPOSTA", "REUNIÃO", "EVENTO"]
    partes = ['<p class="lead">Cada registro identifica <strong>tipo de atuação</strong> (autoria, relatoria, gestão, '
              "articulação…), cargo exercido, período, resultado documentado e fontes com nível de evidência. "
              "Participação não é convertida em autoria; proposta não é apresentada como entrega.</p>"]
    for tipo in ordem_tipos:
        if tipo not in grupos:
            continue
        regs = grupos[tipo]
        partes.append("<section><h2>%s <span class='conta'>(%d)</span></h2>%s</section>"
                      % (esc(tipo_rotulo(tipo)), len(regs), lista_registros(regs)))
    conteudo = "<h1>Realizações — base completa</h1>" + "".join(partes)
    pagina("/realizacoes/", "O que Walter Ihoshi fez: realizações, projetos e ações documentadas",
           "Base completa de ações, projetos, entregas e atuações de Walter Ihoshi, cada uma com fonte, "
           "cargo, tipo de atuação e nível de evidência.", conteudo,
           [jsonld_colecao("Realizações de Walter Ihoshi", "Base completa de registros documentados.", "/realizacoes/")],
           trilha=[("Início", "/"), ("Realizações", "/realizacoes/")])

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
        '<p class="breadcrumb"><a href="%s">Início</a> / <a href="%s">Realizações</a> / %s</p>'
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
        "</article>%s%s"
    ) % (
        l("/"), l("/realizacoes/"), esc(r["titulo"]),
        esc(tipo_rotulo(r["tipo"])), badge_evidencia(r["evidence_score"]),
        esc(r["titulo"]), esc(r["resumo"]), nota_ev,
        fmt_data(r.get("data")), (' <span class="periodo">(%s)</span>' % esc(r["periodo"])) if r.get("periodo") else "",
        esc(r["cargo"]), esc(tipo_rotulo(r["tipo"])), esc(r.get("tipo_detalhe", "")),
        chip_municipios(r["municipios"]) or "—", chip_temas(r["temas"]) or "—",
        proposicao,
        esc(r["o_que_aconteceu"]), esc(r["participacao"]), esc(r["relevancia"]), esc(r["resultado"]),
        entidades or "<li>—</li>",
        sec_fontes(r["fontes"], "Documentos e fontes"),
        share, relacionadas,
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
    conteudo = (
        "<h1>Atuação por tema</h1>"
        '<p class="lead">Páginas temáticas reúnem os registros do acervo por assunto. Temas sem conteúdo documental '
        "suficiente não recebem página de realização — apenas indicação de existência de proposta eleitoral.</p>"
        '<div class="grade-grade">%s</div>' % cards
    )
    pagina("/temas/", "Walter Ihoshi por tema: micro e pequenas empresas, crédito, saúde, desburocratização e mais",
           "Organização temática da atuação documentada de Walter Ihoshi.",
           conteudo, [jsonld_colecao("Temas", "Organização temática do acervo.", "/temas/")],
           trilha=[("Início", "/"), ("Temas", "/temas/")])

def pag_tema(t):
    regs = [r for r in REALIZACOES if t["id"] in r["temas"]]
    cargos = ", ".join(esc(c) for c in t["cargos"]) or "—"
    alerta = ""
    if t.get("apenas_proposta"):
        alerta = ('<div class="alerta"><strong>Transparência:</strong> nesta versão do acervo não há realização '
                  "documentada neste tema. Existe proposta de campanha para 2026, registrada como proposta — não como "
                  "entrega.</div>")
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / <a href="%s">Temas</a> / %s</p>'
        "<h1><span class=\"tema-emoji grande\">%s</span> Walter Ihoshi e %s</h1>"
        '<p class="lead">%s</p>%s'
        '<dl class="ficha"><dt>Cargos em que atuou no tema</dt><dd>%s</dd>'
        "<dt>Registros documentados</dt><dd>%d</dd></dl>"
        "<h2>Principais ações documentadas</h2>%s"
        "<h2>Localidades relacionadas</h2><p>%s</p>"
        "%s"
    ) % (
        l("/"), l("/temas/"), esc(t["nome"]),
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
    conteudo = (
        "<h1>Atuação por localidade</h1>"
        '<p class="lead">Páginas territoriais existem apenas onde há evidência real de atuação. A regional de Marília, '
        "dirigida por Walter Ihoshi a partir de 2023, atende 51 municípios — mas só têm página individual aqueles com "
        "registros documentados. Nenhuma página territorial vazia é criada.</p>"
        '<div class="grade-grade">%s</div>' % cards
    )
    pagina("/municipios/", "Walter Ihoshi por município: ações, projetos e atuação",
           "Onde Walter Ihoshi atuou: páginas territoriais com registros documentados.",
           conteudo, [jsonld_colecao("Municípios", "Organização territorial do acervo.", "/municipios/")],
           trilha=[("Início", "/"), ("Municípios", "/municipios/")])

def pag_municipio(m):
    regs = [r for r in REALIZACOES if m["id"] in r["municipios"]]
    destaques = "".join("<li>%s</li>" % esc(d) for d in m["destaques"])
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / <a href="%s">Municípios</a> / %s</p>'
        "<h1>Walter Ihoshi em %s: ações, projetos e atuação</h1>"
        '<p class="lead">%s</p>'
        "<h2>Histórico de atuação</h2><ul class='marcas'>%s</ul>"
        "<h2>Registros do acervo</h2>%s"
        "<h2>Assuntos relacionados</h2><p>%s</p>"
        "%s"
    ) % (
        l("/"), l("/municipios/"), esc(m["nome"]),
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
            '<li class="tl-item"><div class="tl-ano">%s</div><div class="tl-corpo"><h2>%s</h2>'
            "<p>%s</p>%s<p class='tl-fontes'>Fontes: %s</p></div></li>"
            % (esc(str(ev["ano"])), esc(ev["titulo"]), esc(ev["texto"]), link,
               ", ".join(esc(F[f]["nome"]) for f in ev["fontes"] if f in F))
        )
    conteudo = (
        "<h1>Linha do tempo — trajetória pública (1961–2026)</h1>"
        '<p class="lead">Marcos documentais da trajetória de Walter Shindi Iihoshi. Cada marco aponta para fontes e, '
        "quando existente, para a página de registro detalhada.</p>"
        '<ol class="timeline">%s</ol>' % "".join(itens)
    )
    pagina("/linha-do-tempo/", "Linha do tempo: a trajetória de Walter Ihoshi (1961–2026)",
           "Histórico cronológico documentado: formação, comércio, ACSP, Jabaquara, três mandatos, Jucesp, convênios e candidatura 2026.",
           conteudo, [jsonld_colecao("Linha do tempo", "Trajetória cronológica documentada.", "/linha-do-tempo/")],
           trilha=[("Início", "/"), ("Linha do tempo", "/linha-do-tempo/")])

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
    migalha = '<p class="breadcrumb"><a href="%s">Início</a> / Mandatos</p>' % l("/")
    conteudo = migalha + (
        "<h1>Atuação parlamentar na Câmara dos Deputados</h1>"
        '<p class="lead">Walter Ihoshi exerceu mandatos de deputado federal por São Paulo em três legislaturas. '
        "Nas de 2011 e 2015 entrou como suplente e foi efetivado ao longo da legislatura — este acervo diferencia "
        "eleição, suplência e exercício.</p>"
        "<h2>Legislaturas e exercício</h2>"
        '<table class="tabela"><thead><tr><th>Cargo</th><th>Período</th><th>Partido</th></tr></thead>'
        "<tbody>" + tabela + "</tbody></table>"
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
        '<table class="tabela"><thead><tr><th>Ano</th><th>Partido</th><th>Resultado</th><th>Votos</th></tr></thead>'
        "<tbody>" + elei + "</tbody></table>"
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
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / Jucesp</p>'
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
        l("/"),
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
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / Convênios</p>'
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
        l("/"), l("/fontes/"),
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
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / Comunidade nikkei</p>'
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
        l("/"),
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
    migalha = '<p class="breadcrumb"><a href="%s">Início</a> / Fontes e método</p>' % l("/")
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
        '<table class="tabela"><thead><tr><th>Escala</th><th>Critério</th></tr></thead><tbody>' + niveis + "</tbody></table>"
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
    migalha = '<p class="breadcrumb"><a href="%s">Início</a> / Atualizações</p>' % l("/")
    conteudo = migalha + (
        "<h1>Últimas atualizações do acervo</h1>"
        '<p class="lead">Não é um portal de notícias: esta página registra apenas novos registros incorporados ao '
        "acervo, com fonte, tema e município.</p>"
        "<ul class='atualizacoes atualizacoes-pagina'>" + itens + "</ul>"
    )
    pagina("/atualizacoes/", "Atualizações do acervo — novos registros incorporados",
           "Novos registros incorporados ao acervo de Walter Ihoshi, com fontes, temas e municípios.",
           conteudo, [jsonld_colecao("Atualizações", "Registro de incorporações ao acervo.", "/atualizacoes/")],
           trilha=[("Início", "/"), ("Atualizações", "/atualizacoes/")])

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
                '<li class="clip-item"><div class="clip-esq">%s</div>'
                '<div><a href="%s" target="_blank" rel="noopener nofollow">%s</a>'
                "<p class='clip-meta'>%s &middot; nível da fonte: %s%s%s</p></div></li>"
                % (
                    badge_evidencia(min(c.get("fonte_nivel", 60), 100)),
                    esc(c["link"]), esc(c["titulo"]), esc(c.get("fonte", "")),
                    c.get("fonte_nivel", "—"),
                    (" &middot; " + esc(T[c["tema_proposto"]]["nome"])) if c.get("tema_proposto") and c["tema_proposto"] in T else "",
                    (" &middot; " + esc(M[c["municipio_proposto"]]["nome"])) if c.get("municipio_proposto") and c["municipio_proposto"] in M else "",
                )
                for c in por_dia[d]
            )
            blocos.append("<section class='clip-dia'><h2>%s <span class='conta'>(%d)</span></h2><ul class='clip-lista'>%s</ul></section>" % (esc(rotulo), len(por_dia[d]), linhas))
        corpo = "".join(blocos)
        atualizado = ("Última coleta: <strong>%s</strong>." % esc(str(CLIPPING_ATUALIZADO_EM)[:10].replace("-", "/"))) if CLIPPING_ATUALIZADO_EM else ""
    else:
        corpo = ("<p class='lead'>Ainda não há menções coletadas. A rotina diária de monitoramento (duas execuções "
                 "por dia) alimenta automaticamente esta página com tudo o que a imprensa e as fontes oficiais "
                 "publicarem sobre Walter Ihoshi.</p>")
        atualizado = ""
    migalha = '<p class="breadcrumb"><a href="%s">Início</a> / Clipping</p>' % l("/")
    conteudo = migalha + (
        "<h1>Clipping do dia — menções a Walter Ihoshi</h1>"
        '<p class="lead">Monitoramento diário e automático do nome <strong>Walter Ihoshi / Walter Iihoshi</strong> '
        "na imprensa e em fontes oficiais. Cada menção leva ao veículo original.</p>"
        "<div class='alerta'><strong>Como ler esta página:</strong> o clipping registra menções — a existência da "
        "matéria é o fato documentado. Ele não equivale aos <a href='%s'>registros verificados do acervo</a>: menções "
        "com conteúdo relevante são validadas (fonte, tipo de atuação, resultado) e promovidas a registros com nível "
        "de evidência.</div>%s" % (l("/realizacoes/"), atualizado)
    ) + corpo
    pagina("/clipping/", "Clipping do dia: o que a imprensa publica sobre Walter Ihoshi",
           "Monitoramento diário de menções a Walter Ihoshi (Walter Iihoshi) na imprensa e em fontes oficiais, "
           "com link para cada matéria e separação clara entre menção e registro verificado.",
           conteudo,
           [jsonld_colecao("Clipping diário", "Menções a Walter Ihoshi coletadas automaticamente.", "/clipping/")],
           trilha=[("Início", "/"), ("Clipping", "/clipping/")])


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

JS_BUSCA = """
(function(){
  var dados = JSON.parse(document.getElementById('dados-busca').textContent);
  var normalizar = function(s){return s.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');};
  var input = document.getElementById('campo-busca');
  var saida = document.getElementById('resultados');
  function render(q){
    var termo = normalizar(q.trim());
    if(termo.length < 2){ saida.innerHTML = '<p class="dica">Digite ao menos duas letras. Exemplos: JUCESP, Cadastro Positivo, Marília, microempresas, Japão.</p>'; return; }
    var palavras = termo.split(/\\s+/);
    var resultados = [];
    dados.forEach(function(item){
      var alvo = normalizar(item.ch + ' ' + item.t + ' ' + item.d);
      var pontos = 0;
      palavras.forEach(function(p){
        if(alvo.indexOf(p) === -1){ pontos = -999; } else if(normalizar(item.t).indexOf(p) !== -1){ pontos += 3; } else { pontos += 1; }
      });
      if(pontos > 0){ resultados.push([pontos, item]); }
    });
    resultados.sort(function(a,b){ return b[0]-a[0]; });
    if(!resultados.length){ saida.innerHTML = '<p class="dica">Nenhum resultado para “' + q.replace(/[<>&]/g,'') + '” nesta versão do acervo.</p>'; return; }
    var html = '';
    resultados.slice(0, 60).forEach(function(par){
      var item = par[1];
      html += '<article class="card"><span class="tag-tipo">' + item.cat + '</span><h3><a href="' + item.u + '">' +
        item.t.replace(/[<>&]/g, function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];}) + '</a></h3><p>' +
        item.d.replace(/[<>&]/g, function(c){return {'<':'&lt;','>':'&gt;','&':'&amp;'}[c];}) + '</p></article>';
    });
    saida.innerHTML = '<p class="conta-resultados">' + resultados.length + ' resultado(s)</p><div class="grade">' + html + '</div>';
  }
  input.addEventListener('input', function(){ render(input.value); });
  var qs = new URLSearchParams(window.location.search).get('q');
  if(qs){ input.value = qs; render(qs); } else { render(''); }
})();
"""

def pag_busca():
    itens = montar_indice_busca()
    dados_json = json.dumps(itens, ensure_ascii=False).replace("</", "<\\/")
    conteudo = (
        '<p class="breadcrumb"><a href="%s">Início</a> / Busca</p>'
        "<h1>Busca no acervo</h1>"
        '<p class="lead">Pesquise realizações, municípios, temas, cargos, proposições e marcos da linha do tempo.</p>'
        '<form onsubmit="return false"><input id="campo-busca" type="search" placeholder="Pesquise por município, projeto ou assunto" '
        'aria-label="Campo de busca" autocomplete="off"></form>'
        '<div id="resultados" aria-live="polite"></div>'
        '<script type="application/json" id="dados-busca">%s</script>'
        "<script>%s</script>"
    ) % (l("/"), dados_json, JS_BUSCA)
    pagina("/busca/", "Busca no acervo de Walter Ihoshi",
           "Pesquise por município, projeto ou assunto na trajetória documentada de Walter Ihoshi.",
           conteudo, [jsonld_colecao("Busca", "Busca no acervo.", "/busca/")],
           trilha=[("Início", "/"), ("Busca", "/busca/")])

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

JS_COPIAR = """
document.addEventListener('click', function(e){
  if(e.target && e.target.classList && e.target.classList.contains('copiar')){
    var url = e.target.getAttribute('data-url');
    if(navigator.clipboard){ navigator.clipboard.writeText(url).then(function(){ e.target.textContent = 'Link copiado!'; }); }
    else { e.target.textContent = url; }
  }
});
"""

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

    # script auxiliar de compartilhamento
    with open(os.path.join(SAIDA, "static", "app.js"), "w", encoding="utf-8") as f:
        f.write(JS_COPIAR)

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
