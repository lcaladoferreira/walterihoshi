#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de UX e acessibilidade do site gerado em public/.

Roda DEPOIS de scripts/gerar.py e checa o HTML/CSS/JS que de fato sai do build
(não uma reimplementação dele). Cada checagem aponta um comportamento que o
visitante percebe; quando algo falha, o script diz em quais páginas.

Uso:
    python3 scripts/gerar.py && python3 scripts/testar_ux.py

Sai com código 1 se qualquer checagem falhar (dá para plugar no CI).
"""
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "public")
STATIC = os.path.join(RAIZ, "static")
BASE = json.load(open(os.path.join(RAIZ, "data", "config.json"), encoding="utf-8"))["base_path"].rstrip("/")

FALHAS = []
AVISOS = []
OK = []


def registrar(nome, problemas, aviso=False):
    if problemas:
        (AVISOS if aviso else FALHAS).append((nome, problemas))
    else:
        OK.append(nome)


def paginas_html():
    achadas = []
    for pasta, _, arquivos in os.walk(SAIDA):
        for a in arquivos:
            if a.endswith(".html"):
                achadas.append(os.path.join(pasta, a))
    return sorted(achadas)


def relativo(caminho):
    return "/" + os.path.relpath(caminho, SAIDA).replace(os.sep, "/")


def corpo_da_pagina(texto):
    """Só o conteúdo principal: sem cabeçalho, sem rodapé, sem bloco <noscript>.
    Contar <h2> do documento inteiro mediria o rodapé, não a página."""
    trecho = texto.split('<div class="pagina-corpo">', 1)[-1]
    trecho = trecho.split("</main>", 1)[0]
    return re.sub(r"<noscript>.*?</noscript>", "", trecho, flags=re.S)


# ------------------------------------------------------------------ parser
class Extrator(HTMLParser):
    """Coleta o mínimo necessário para auditar a página sem dependências."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.tags = []
        self.ids = set()
        self.h1 = 0
        self.inputs = []          # (tag, attrs)
        self.labels_for = set()
        self.hrefs = []
        self.ordem_foco = []      # primeiros elementos focáveis do documento
        self.landmarks = []
        self.sem_rotulo = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "label" and a.get("for"):
            self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            self.inputs.append((tag, a))
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag in ("header", "nav", "main", "footer", "aside"):
            self.landmarks.append((tag, a.get("aria-label")))
        if tag in ("a", "button", "input", "select", "summary") and len(self.ordem_foco) < 3:
            self.ordem_foco.append((tag, a))


def analisar(caminho):
    texto = open(caminho, encoding="utf-8").read()
    p = Extrator()
    p.feed(texto)
    p.texto = texto
    return p


# ------------------------------------------------------------------ checagens
def chk_estrutura():
    """Toda página precisa do esqueleto de navegação assistiva completo."""
    problemas = []
    for c in paginas_html():
        t = open(c, encoding="utf-8").read()
        r = relativo(c)
        faltando = []
        for pedaco, rotulo in [
            ('class="pular-conteudo"', "link de pular para o conteúdo"),
            ('<main id="conteudo" tabindex="-1">', "main focável"),
            ('class="container pagina', "container limitando a largura do conteúdo"),
            ('id="avisos"', "região de avisos (aria-live)"),
            ('id="alternar-tema"', "seletor de tema"),
            ('id="menu-lateral"', "menu lateral"),
            ('id="voltar-topo"', "botão voltar ao topo"),
            ('<script src="%s/static/app.js" defer>' % BASE, "app.js carregado"),
            ('<html lang="pt-BR"', "idioma declarado"),
            ('name="viewport"', "viewport responsivo"),
        ]:
            if pedaco not in t:
                faltando.append(rotulo)
        if faltando:
            problemas.append("%s → falta: %s" % (r, ", ".join(faltando)))
        # o link de pular precisa ser o primeiro elemento do corpo
        corpo = t.split("<body>", 1)[-1]
        if not corpo.lstrip().startswith('<a class="pular-conteudo"'):
            problemas.append("%s → link de pular não é o primeiro elemento do <body>" % r)
    registrar("Estrutura de página (skip link, main focável, container, live region, tema, menu)", problemas)


def chk_navegacao():
    """Menu: estado expandido declarado, drawer modal, item atual marcado."""
    problemas = []
    for c in paginas_html():
        p = analisar(c)
        r = relativo(c)
        botao = [a for t, a in p.tags if a.get("id") == "abrir-menu"]
        if botao:
            b = botao[0]
            if b.get("aria-expanded") not in ("true", "false"):
                problemas.append("%s → botão de menu sem aria-expanded" % r)
            if b.get("aria-controls") != "menu-lateral":
                problemas.append("%s → botão de menu sem aria-controls válido" % r)
        drawer = [a for t, a in p.tags if a.get("id") == "menu-lateral"]
        if drawer:
            d = drawer[0]
            if d.get("role") != "dialog" or d.get("aria-modal") != "true":
                problemas.append("%s → drawer não é dialog modal" % r)
            if d.get("aria-hidden") != "true":
                problemas.append("%s → drawer começa visível para leitores de tela" % r)
        if p.h1 != 1:
            problemas.append("%s → %d <h1> (deveria ser exatamente 1)" % (r, p.h1))
    registrar("Navegação (menu acessível, drawer modal, h1 único por página)", problemas)


def chk_trilha():
    """Trilha de navegação é landmark, não texto decorativo."""
    problemas = []
    for c in paginas_html():
        r = relativo(c)
        if r.endswith("/index.html") and r == "/index.html":
            continue
        if r == "/404.html":
            continue
        t = open(c, encoding="utf-8").read()
        if 'class="breadcrumb"' in t:
            problemas.append("%s → trilha antiga em <p class=\"breadcrumb\">" % r)
        if '<nav class="trilha" aria-label="Trilha de navegação"><ol>' not in t:
            problemas.append("%s → sem <nav class=\"trilha\"> com <ol>" % r)
    registrar("Trilha de navegação como landmark (<nav> + <ol>) em toda página interna", problemas)


def chk_formularios():
    """Todo campo tem nome acessível — placeholder não conta como rótulo."""
    problemas = []
    for c in paginas_html():
        p = analisar(c)
        r = relativo(c)
        for tag, a in p.inputs:
            if a.get("type") in ("hidden", "submit", "checkbox", "radio"):
                continue
            tem_nome = (a.get("id") in p.labels_for or a.get("aria-label")
                        or a.get("aria-labelledby") or a.get("title"))
            if not tem_nome:
                problemas.append("%s → <%s id=%s> sem rótulo acessível" % (r, tag, a.get("id")))
        # checkbox/radio precisam de label envolvendo ou aria-label
        for tag, a in p.inputs:
            if a.get("type") in ("checkbox", "radio") and not a.get("aria-label") \
               and a.get("id") not in p.labels_for and "aria-label" not in a:
                # aceita <label class="chip-opcao"><input ...> (label envolvendo)
                if 'id="%s"' % a.get("id") in p.texto and p.texto.count('<label class="chip-opcao"') == 0:
                    problemas.append("%s → <%s id=%s> sem rótulo" % (r, tag, a.get("id")))
    registrar("Campos de formulário com nome acessível", problemas)


def chk_facetas():
    """A página de base precisa de filtros, contagem falada e estado vazio."""
    alvo = os.path.join(SAIDA, "realizacoes", "index.html")
    if not os.path.exists(alvo):
        registrar("Facetas em /realizacoes/", ["/realizacoes/index.html não existe"])
        return
    t = open(alvo, encoding="utf-8").read()
    realizacoes = json.load(open(os.path.join(RAIZ, "data", "realizacoes.json"), encoding="utf-8"))["realizacoes"]
    problemas = []
    for pedaco, rotulo in [
        ('id="filtros-realizacoes"', "painel de filtros"),
        ('id="f-texto"', "filtro por texto"),
        ('id="f-tema"', "filtro por tema"),
        ('id="f-municipio"', "filtro por município"),
        ('id="f-evidencia"', "filtro por nível de evidência"),
        ('id="f-ordem"', "ordenador"),
        ('id="filtro-contagem" role="status" aria-live="polite"', "contagem anunciada"),
        ('id="filtro-aviso"', "estado vazio dos filtros"),
        ('id="carregar-mais"', "revelação progressiva"),
        ('id="limpar-filtros"', "ação de limpar filtros"),
        ('data-densidade="densa"', "alternador de densidade"),
    ]:
        if pedaco not in t:
            problemas.append("falta %s" % rotulo)
    cartoes = re.findall(r'<article class="card" data-id="([^"]+)"', t)
    if len(cartoes) != len(realizacoes):
        problemas.append("%d cartões renderizados para %d registros" % (len(cartoes), len(realizacoes)))
    if len(set(cartoes)) != len(cartoes):
        problemas.append("há cartões duplicados")
    for att in ("data-tipo", "data-temas", "data-municipios", "data-ev", "data-ordem", "data-texto"):
        if t.count(att) < len(realizacoes):
            problemas.append("atributo %s ausente em algum cartão" % att)
    # os 12 primeiros visíveis: o resto precisa chegar com hidden (revelação progressiva)
    registrar("Facetas em /realizacoes/ (filtros, contagem, estado vazio, dados p/ filtrar)", problemas)


def chk_busca():
    alvo = os.path.join(SAIDA, "busca", "index.html")
    if not os.path.exists(alvo):
        registrar("Página de busca", ["/busca/index.html não existe"])
        return
    t = open(alvo, encoding="utf-8").read()
    problemas = []
    for pedaco, rotulo in [
        ('id="campo-busca"', "campo de busca"),
        ('id="dados-busca"', "índice embutido"),
        ('id="resultados"', "área de resultados"),
        ('id="conta-resultados"', "contador de resultados"),
        ('id="limpar-busca"', "botão limpar"),
        ("<noscript>", "alternativa sem JavaScript"),
        ('role="search"', "formulário marcado como busca"),
    ]:
        if pedaco not in t:
            problemas.append("falta %s" % rotulo)
    m = re.search(r'<script type="application/json" id="dados-busca">(.*?)</script>', t, re.S)
    if not m:
        problemas.append("índice de busca não encontrado")
    else:
        try:
            dados = json.loads(m.group(1))
            if len(dados) < 40:
                problemas.append("índice com apenas %d itens" % len(dados))
            for item in dados:
                if not all(k in item for k in ("t", "d", "u", "cat", "ch")):
                    problemas.append("item do índice incompleto: %r" % item.get("t"))
                    break
        except ValueError as e:
            problemas.append("índice de busca inválido: %s" % e)
    registrar("Busca (campo, índice válido, contador, limpar, alternativa sem JS)", problemas)


def chk_links():
    """Nenhum link interno pode apontar para o vazio — 404 é falha de UX."""
    problemas = []
    for c in paginas_html():
        p = analisar(c)
        r = relativo(c)
        for href in p.hrefs:
            if href.startswith("#") or href.startswith("mailto:"):
                if href == "#":
                    problemas.append("%s → link morto href=\"#\"" % r)
                elif len(href) > 1:
                    if href[1:] not in p.ids:
                        problemas.append("%s → âncora %s não existe na página" % (r, href))
                continue
            parsed = urlparse(href)
            if parsed.netloc:
                continue
            caminho = parsed.path
            if not caminho.startswith(BASE + "/") and caminho != BASE:
                continue
            resto = caminho[len(BASE):] or "/"
            destino = os.path.normpath(os.path.join(SAIDA, resto.lstrip("/")))
            if resto.endswith("/") or resto == "/":
                destino = os.path.join(destino, "index.html")
            if not os.path.exists(destino):
                problemas.append("%s → %s não existe" % (r, href))
    registrar("Integridade de links internos e âncoras", problemas[:25] + (["…"] if len(problemas) > 25 else []))


def chk_estados_vazios():
    """Onde pode não haver conteúdo, precisa haver um estado declarado."""
    css = open(os.path.join(STATIC, "estilo.css"), encoding="utf-8").read()
    problemas = []
    for classe in (".estado", ".estado-vazio", ".estado-erro", ".esqueleto"):
        if classe not in css:
            problemas.append("CSS não define %s" % classe)
    gerador = open(os.path.join(RAIZ, "scripts", "gerar.py"), encoding="utf-8").read()
    if "def estado_vazio(" not in gerador:
        problemas.append("gerador não tem componente de estado vazio")
    if "estado_vazio(" in gerador and gerador.count("estado_vazio(") < 3:
        problemas.append("estado vazio usado em menos de 2 lugares")
    registrar("Estados vazios e de erro definidos e usados", problemas)


def _luminancia(hexa):
    hexa = hexa.lstrip("#")
    canais = []
    for i in (0, 2, 4):
        v = int(hexa[i:i + 2], 16) / 255.0
        canais.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    r, g, b = canais
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def chk_contraste():
    """Texto informativo pequeno precisa de 4,5:1 (WCAG 2.1 AA)."""
    css = open(os.path.join(STATIC, "estilo.css"), encoding="utf-8").read()
    blocos = re.findall(r":root\s*\{(.*?)\n\}", css, re.S)
    if not blocos:
        registrar("Contraste dos tokens de texto", ["não foi possível ler os tokens :root"])
        return
    tokens = {}
    for bloco in blocos:
        for nome, valor in re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", bloco):
            tokens.setdefault(nome, valor)
    escuro = {}
    m = re.search(r':root\[data-tema="escuro"\]\s*\{(.*?)\n\}', css, re.S)
    if m:
        for nome, valor in re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})", m.group(1)):
            escuro[nome] = valor
    problemas = []
    for tema, tk in (("claro", tokens), ("escuro", dict(tokens, **escuro))):
        fundo_cartao = tk.get("--cartao", "#ffffff")
        fundo_papel = tk.get("--papel", "#ffffff")
        for token in ("--tinta", "--tinta-2", "--tinta-3"):
            cor = tk.get(token)
            if not cor:
                continue
            for fundo_nome, fundo in (("--cartao", fundo_cartao), ("--papel", fundo_papel)):
                relacao = _contraste(cor, fundo)
                if relacao < 4.5:
                    problemas.append("%s %s sobre %s: %.2f:1 (mínimo 4,5:1)"
                                     % (tema, token, fundo_nome, relacao))
    registrar("Contraste dos tokens de texto (WCAG AA, mínimo 4,5:1)", problemas)


def chk_alvos_e_foco():
    css = open(os.path.join(STATIC, "estilo.css"), encoding="utf-8").read()
    problemas = []
    if "--alvo: 44px" not in css and "--alvo:44px" not in css:
        problemas.append("não há token de área mínima de toque de 44px")
    if ":focus-visible" not in css:
        problemas.append("sem estilo de :focus-visible")
    for media, rotulo in [("@media (prefers-reduced-motion", "movimento reduzido"),
                          ("@media (prefers-contrast", "alto contraste"),
                          ("@media print", "impressão")]:
        if media not in css:
            problemas.append("sem bloco para %s" % rotulo)
    if ".sr-only" not in css:
        problemas.append("sem utilitário .sr-only")
    registrar("Alvos de toque, foco visível e preferências do usuário", problemas)


def chk_js():
    js = open(os.path.join(STATIC, "app.js"), encoding="utf-8").read()
    problemas = []
    for modulo in ("moduloTema", "moduloMenu", "moduloNav", "moduloLeitura", "moduloSumario",
                   "moduloCopiar", "moduloFiltros", "moduloBusca", "moduloAnos",
                   "moduloClipping", "moduloAtalhos"):
        if modulo not in js:
            problemas.append("módulo %s ausente" % modulo)
    for pedaco, rotulo in [
        ("Escape", "tecla Esc fecha sobreposições"),
        ("aria-expanded", "estado expandido sincronizado"),
        ("replaceState", "estado dos filtros na URL"),
        ("localStorage", "preferências persistidas"),
        ("requestAnimationFrame", "scroll sem travar a pintura"),
        ("prefers-reduced-motion", "respeito a movimento reduzido"),
        ("<mark>", "realce dos termos encontrados"),
    ]:
        if pedaco not in js:
            problemas.append("JS sem %s" % rotulo)
    if "rodar(" not in js:
        problemas.append("JS sem isolamento de falhas por módulo")
    registrar("Camada de interação (módulos, teclado, estado, resiliência)", problemas)


def chk_404():
    alvo = os.path.join(SAIDA, "404.html")
    problemas = []
    if not os.path.exists(alvo):
        problemas.append("404.html não foi gerado")
    else:
        t = open(alvo, encoding="utf-8").read()
        if "/busca/" not in t:
            problemas.append("404 não oferece a busca como saída")
        if "estado estado-erro" not in t:
            problemas.append("404 não usa o componente de estado de erro")
    sitemap = open(os.path.join(SAIDA, "sitemap.xml"), encoding="utf-8").read()
    if "404.html" in sitemap:
        problemas.append("404.html está no sitemap")
    registrar("Página 404 com caminho de recuperação", problemas)


def chk_sumario():
    """Página longa sem jeito de se orientar é página abandonada no meio.

    Regra: acima de 8 seções de conteúdo, a página precisa de UM mecanismo de
    orientação — sumário, navegação de seções declarada (filtro por década,
    salto por dia) ou, no caso da página inicial, atalhos explícitos no topo.
    Conteúdo dentro de <noscript> não conta como seção.
    """
    problemas = []
    for c in paginas_html():
        t = open(c, encoding="utf-8").read()
        r = relativo(c)
        corpo = corpo_da_pagina(t)
        secoes = len(re.findall(r"<h2[^>]*>", corpo))
        if secoes <= 8:
            continue
        mecanismos = []
        if 'class="sumario"' in t:
            mecanismos.append("sumário")
        if "data-navegacao-secoes" in t:
            mecanismos.append("navegação de seções")
        if r == "/index.html":
            if 'class="atalhos"' in t:
                mecanismos.append("atalhos da página inicial")
        if not mecanismos:
            problemas.append("%s → %d seções e nenhum mecanismo de orientação" % (r, secoes))
    registrar("Orientação em páginas longas (sumário, salto por seção ou atalhos)", problemas)


def chk_hierarquia_titulos():
    """Quem navega por títulos (leitor de tela, Ctrl+Alt+H) depende da ordem.
    Título não pode pular nível, e o chrome da página não pode injetar h2."""
    problemas = []
    for c in paginas_html():
        t = open(c, encoding="utf-8").read()
        r = relativo(c)
        antes = t.split("<main", 1)[0]
        depois = t.split("</main>", 1)[-1]
        for trecho, onde in ((antes, "cabeçalho/menu"), (depois, "rodapé")):
            achados = re.findall(r"<h([2-6])", trecho)
            if achados:
                problemas.append("%s → %d título(s) h%s no %s" % (r, len(achados), achados[0], onde))
        niveis = [int(n) for n in re.findall(r"<h([1-6])[^>]*>", corpo_da_pagina(t))]
        if not niveis or niveis[0] != 1:
            problemas.append("%s → o conteúdo não começa em <h1>" % r)
        for anterior, atual in zip(niveis, niveis[1:]):
            if atual > anterior + 1:
                problemas.append("%s → pula de <h%d> para <h%d>" % (r, anterior, atual))
                break
    registrar("Hierarquia de títulos (sem saltos de nível, chrome sem h2)", problemas)


def chk_saida_sem_janela():
    """O conteúdo principal precisa estar limitado e com respiro lateral."""
    problemas = []
    for c in paginas_html():
        t = open(c, encoding="utf-8").read()
        r = relativo(c)
        if '<main id="conteudo" tabindex="-1"><div class="container pagina' not in t:
            problemas.append("%s → conteúdo principal fora do container" % r)
    registrar("Conteúdo principal dentro do container (largura limitada + respiro)", problemas)


# ------------------------------------------------------------------ saída
def main():
    if not os.path.isdir(SAIDA):
        print("public/ não existe. Rode antes: python3 scripts/gerar.py")
        return 2
    chk_estrutura()
    chk_saida_sem_janela()
    chk_navegacao()
    chk_trilha()
    chk_formularios()
    chk_facetas()
    chk_busca()
    chk_links()
    chk_estados_vazios()
    chk_contraste()
    chk_alvos_e_foco()
    chk_js()
    chk_404()
    chk_sumario()
    chk_hierarquia_titulos()

    total_paginas = len(paginas_html())
    print("=" * 72)
    print("VERIFICAÇÃO DE UX — %d páginas HTML em public/" % total_paginas)
    print("=" * 72)
    for nome in OK:
        print("  ok    %s" % nome)
    for nome, itens in AVISOS:
        print("  aviso %s" % nome)
        for i in itens[:8]:
            print("          - %s" % i)
    for nome, itens in FALHAS:
        print("  FALHA %s" % nome)
        for i in itens[:12]:
            print("          - %s" % i)
        if len(itens) > 12:
            print("          … e mais %d" % (len(itens) - 12))
    print("-" * 72)
    print("%d checagens ok · %d avisos · %d falhas" % (len(OK), len(AVISOS), len(FALHAS)))
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
