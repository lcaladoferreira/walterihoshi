/* =====================================================================
   WALTER IHOSHI — ACERVO DE ATUAÇÃO PÚBLICA
   Camada de interação (progressive enhancement).

   Contrato: o HTML já traz todo o conteúdo. Este arquivo só acrescenta
   velocidade e conveniência. Se ele falhar, o site continua navegável,
   legível e completo — por isso cada módulo é isolado em try/catch e
   nenhum conteúdo é gerado apenas aqui.

   Módulos:
     tema        — claro/escuro/auto, persistido, sem flash de tema errado
     menu        — drawer mobile com foco preso, Esc, cortina e travamento
     nav         — grupos <details> fecham ao clicar fora ou apertar Esc
     leitura     — barra de progresso + voltar ao topo
     sumario     — scroll-spy do índice da página
     copiar      — copiar link com confirmação falada (aria-live)
     filtros     — facetas em /realizacoes/ com estado na URL
     busca       — busca instantânea com realce, teclado e histórico
     anos        — filtro por período na linha do tempo
     clipping    — filtro do clipping do dia
     atalhos     — "/" e Ctrl/Cmd+K levam ao campo de busca
   ===================================================================== */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;

  /* ---------- utilidades ---------- */
  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  function normalizar(s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function escapa(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // O termo buscado é normalizado (sem acentos) para comparar; o texto exibido
  // não é. Cada letra vira uma classe que aceita as variantes acentuadas, e o
  // escape de HTML é feito por pedaço — nunca depois de injetar <mark>.
  var ACENTOS = {
    a: "[aáàâãäå]", e: "[eéèêë]", i: "[iíìîï]", o: "[oóòôõö]",
    u: "[uúùûü]", c: "[cç]", n: "[nñ]", y: "[yýÿ]", d: "[dð]", s: "[sß]"
  };
  function letra(ch) {
    return ACENTOS[ch] || ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
  function realca(texto, termos) {
    var limpos = (termos || []).filter(Boolean);
    if (!limpos.length) return escapa(texto);
    var padrao;
    try {
      padrao = new RegExp("(" + limpos.map(function (t) {
        return t.split("").map(letra).join("");
      }).join("|") + ")", "gi");
    } catch (e) { return escapa(texto); }
    // split com grupo de captura devolve [antes, achado, depois, achado, …]
    return String(texto == null ? "" : texto).split(padrao).map(function (pedaco, i) {
      return i % 2 === 1 ? "<mark>" + escapa(pedaco) + "</mark>" : escapa(pedaco);
    }).join("");
  }

  function anuncia(msg) {
    var regio = $("#avisos");
    if (regio) regio.textContent = msg;
  }

  function memoria() {
    try {
      var k = "__teste__";
      window.localStorage.setItem(k, k);
      window.localStorage.removeItem(k);
      return window.localStorage;
    } catch (e) { return null; }
  }
  var loja = memoria();

  function guardar(chave, valor) { if (loja) { try { loja.setItem(chave, valor); } catch (e) {} } }
  function ler(chave) { if (!loja) return null; try { return loja.getItem(chave); } catch (e) { return null; } }

  function rodar(nome, fn) {
    try { fn(); } catch (erro) {
      if (window.console && console.warn) console.warn("[ux] módulo " + nome + " falhou:", erro);
    }
  }

  /* ================================================================
     TEMA — claro / escuro / automático
     ================================================================ */
  var CHAVE_TEMA = "wi-tema";
  var ROTULOS_TEMA = {
    auto: { icone: "🌗", texto: "Tema: automático (segue o sistema)" },
    claro: { icone: "☀️", texto: "Tema: claro" },
    escuro: { icone: "🌙", texto: "Tema: escuro" }
  };

  function aplicarTema(modo, avisar) {
    if (!ROTULOS_TEMA[modo]) modo = "auto";
    root.setAttribute("data-tema", modo);
    guardar(CHAVE_TEMA, modo);
    var botao = $("#alternar-tema");
    if (botao) {
      var rot = ROTULOS_TEMA[modo];
      var icone = $(".icone", botao);
      if (icone) icone.textContent = rot.icone;
      botao.setAttribute("aria-label", rot.texto + " — ativar para mudar");
      botao.setAttribute("title", rot.texto);
    }
    if (avisar) anuncia("Tema alterado para " + modo + ".");
  }

  function moduloTema() {
    aplicarTema(ler(CHAVE_TEMA) || root.getAttribute("data-tema") || "auto", false);
    var botao = $("#alternar-tema");
    if (!botao) return;
    botao.addEventListener("click", function () {
      var atual = root.getAttribute("data-tema") || "auto";
      var proximo = atual === "auto" ? "claro" : (atual === "claro" ? "escuro" : "auto");
      aplicarTema(proximo, true);
    });
  }

  /* ================================================================
     MENU MOBILE — drawer acessível
     ================================================================ */
  var FOCAVEIS = 'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

  function moduloMenu() {
    var botao = $("#abrir-menu");
    var drawer = $("#menu-lateral");
    var cortina = $("#cortina-menu");
    if (!botao || !drawer) return;
    var ultimoFoco = null;

    function focaveis() {
      return $$(FOCAVEIS, drawer).filter(function (el) { return el.offsetParent !== null; });
    }
    function abrir() {
      ultimoFoco = doc.activeElement;
      doc.body.classList.add("menu-aberto");
      botao.setAttribute("aria-expanded", "true");
      drawer.setAttribute("aria-hidden", "false");
      var primeiro = focaveis()[0];
      if (primeiro) primeiro.focus();
      doc.addEventListener("keydown", aoTeclar);
    }
    function fechar() {
      doc.body.classList.remove("menu-aberto");
      botao.setAttribute("aria-expanded", "false");
      drawer.setAttribute("aria-hidden", "true");
      doc.removeEventListener("keydown", aoTeclar);
      if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
    }
    function aoTeclar(e) {
      if (e.key === "Escape" || e.key === "Esc") { e.preventDefault(); fechar(); return; }
      if (e.key !== "Tab") return;
      var lista = focaveis();
      if (!lista.length) return;
      var primeiro = lista[0], ultimo = lista[lista.length - 1];
      if (e.shiftKey && doc.activeElement === primeiro) { e.preventDefault(); ultimo.focus(); }
      else if (!e.shiftKey && doc.activeElement === ultimo) { e.preventDefault(); primeiro.focus(); }
    }

    botao.addEventListener("click", function () {
      if (doc.body.classList.contains("menu-aberto")) fechar(); else abrir();
    });
    if (cortina) cortina.addEventListener("click", fechar);
    // fechar ao navegar (links do drawer) e ao voltar na história
    $$("a", drawer).forEach(function (a) { a.addEventListener("click", fechar); });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 1000 && doc.body.classList.contains("menu-aberto")) fechar();
    });
    window.fecharMenuLateral = fechar;
  }

  /* ================================================================
     NAV — grupos <details> fecham sozinhos
     ================================================================ */
  function moduloNav() {
    var grupos = $$("details.nav-grupo");
    if (!grupos.length) return;
    grupos.forEach(function (g) {
      g.addEventListener("toggle", function () {
        if (!g.open) return;
        grupos.forEach(function (outro) { if (outro !== g) outro.open = false; });
      });
    });
    doc.addEventListener("click", function (e) {
      grupos.forEach(function (g) { if (g.open && !g.contains(e.target)) g.open = false; });
    });
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" || e.key === "Esc") grupos.forEach(function (g) { g.open = false; });
    });
  }

  /* ================================================================
     LEITURA — progresso + voltar ao topo
     ================================================================ */
  function moduloLeitura() {
    var barra = $("#progresso-leitura");
    var topo = $("#voltar-topo");
    var ticking = false;

    function atualizar() {
      ticking = false;
      var altura = doc.documentElement.scrollHeight - window.innerHeight;
      var y = window.pageYOffset || doc.documentElement.scrollTop;
      if (barra) barra.style.width = (altura > 0 ? Math.min(100, (y / altura) * 100) : 0) + "%";
      if (topo) topo.classList.toggle("visivel", y > 520);
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(atualizar); }
    }, { passive: true });
    window.addEventListener("resize", atualizar);
    atualizar();

    if (topo) {
      topo.addEventListener("click", function () {
        var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        window.scrollTo({ top: 0, behavior: reduz ? "auto" : "smooth" });
        var pular = $("#conteudo");
        if (pular) pular.focus({ preventScroll: true });
      });
    }
  }

  /* ================================================================
     SUMÁRIO — scroll-spy
     ================================================================ */
  function moduloSumario() {
    var links = $$(".sumario a[href^='#']");
    if (links.length < 2) return;
    var alvos = links.map(function (a) {
      return doc.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
    }).filter(Boolean);
    if (!alvos.length) return;

    function marcar() {
      var offset = (parseFloat(getComputedStyle(root).getPropertyValue("--topo-altura")) || 62) + 40;
      var atual = alvos[0];
      alvos.forEach(function (sec) {
        if (sec.getBoundingClientRect().top - offset <= 0) atual = sec;
      });
      links.forEach(function (a) {
        var eh = a.getAttribute("href") === "#" + atual.id;
        a.classList.toggle("ativo", eh);
        if (eh) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
      });
    }
    var ticking = false;
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(function () { ticking = false; marcar(); }); }
    }, { passive: true });
    marcar();
  }

  /* ================================================================
     COPIAR LINK — com confirmação visível e falada
     ================================================================ */
  function moduloCopiar() {
    doc.addEventListener("click", function (e) {
      var botao = e.target && e.target.closest ? e.target.closest(".copiar") : null;
      if (!botao) return;
      var url = botao.getAttribute("data-url") || window.location.href;
      var original = botao.textContent;

      function sucesso() {
        botao.classList.add("copiado");
        botao.textContent = "Link copiado ✓";
        anuncia("Link copiado para a área de transferência.");
        window.setTimeout(function () {
          botao.classList.remove("copiado");
          botao.textContent = original;
        }, 2400);
      }
      function falha() {
        botao.textContent = url;
        anuncia("Não foi possível copiar automaticamente. O endereço é " + url);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(sucesso, function () {
          if (copiarManual(url)) sucesso(); else falha();
        });
      } else if (copiarManual(url)) { sucesso(); } else { falha(); }
    });
  }

  function copiarManual(texto) {
    try {
      var area = doc.createElement("textarea");
      area.value = texto;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      doc.body.appendChild(area);
      area.select();
      var ok = doc.execCommand("copy");
      doc.body.removeChild(area);
      return ok;
    } catch (e) { return false; }
  }

  /* ================================================================
     FILTROS — /realizacoes/ (facetas, ordenação, estado na URL)
     ================================================================ */
  var PASSO = 12;

  function moduloFiltros() {
    var painel = $("#filtros-realizacoes");
    var lista = $("#lista-registros");
    if (!painel || !lista) return;

    var cartoes = $$(".card[data-id]", lista);
    var saida = $("#filtro-contagem");
    var aviso = $("#filtro-aviso");
    var botaoMais = $("#carregar-mais");
    var tagsAplicadas = $("#filtros-aplicados");
    var campoTexto = $("#f-texto");
    var campoTema = $("#f-tema");
    var campoMunicipio = $("#f-municipio");
    var campoEvidencia = $("#f-evidencia");
    var campoOrdem = $("#f-ordem");
    var caixasTipo = $$('input[name="tipo"]', painel);
    var grade = $(".grade", lista) || lista;

    var visiveis = PASSO;

    function estado() {
      return {
        q: normalizar((campoTexto && campoTexto.value) || ""),
        tipos: caixasTipo.filter(function (c) { return c.checked; }).map(function (c) { return c.value; }),
        tema: (campoTema && campoTema.value) || "",
        municipio: (campoMunicipio && campoMunicipio.value) || "",
        evidencia: parseInt((campoEvidencia && campoEvidencia.value) || "0", 10) || 0,
        ordem: (campoOrdem && campoOrdem.value) || "relevancia"
      };
    }

    function combina(cartao, e) {
      if (e.q && normalizar(cartao.getAttribute("data-texto")).indexOf(e.q) === -1) return false;
      if (e.tipos.length && e.tipos.indexOf(cartao.getAttribute("data-tipo")) === -1) return false;
      if (e.tema && (" " + cartao.getAttribute("data-temas") + " ").indexOf(" " + e.tema + " ") === -1) return false;
      if (e.municipio && (" " + cartao.getAttribute("data-municipios") + " ").indexOf(" " + e.municipio + " ") === -1) return false;
      if (e.evidencia && parseInt(cartao.getAttribute("data-ev"), 10) < e.evidencia) return false;
      return true;
    }

    function ordenar(a, b, ordem) {
      function num(el, att) { return parseInt(el.getAttribute(att), 10) || 0; }
      switch (ordem) {
        case "recente": return (b.getAttribute("data-data") || "").localeCompare(a.getAttribute("data-data") || "");
        case "antigo": return (a.getAttribute("data-data") || "").localeCompare(b.getAttribute("data-data") || "");
        case "evidencia": return num(b, "data-ev") - num(a, "data-ev") || num(a, "data-ordem") - num(b, "data-ordem");
        case "titulo": return (a.getAttribute("data-titulo") || "").localeCompare(b.getAttribute("data-titulo") || "", "pt-BR");
        default: return num(a, "data-ordem") - num(b, "data-ordem");
      }
    }

    function sincronizarUrl(e) {
      if (!window.history || !window.history.replaceState) return;
      var p = new URLSearchParams();
      if (e.q) p.set("q", campoTexto.value.trim());
      e.tipos.forEach(function (t) { p.append("tipo", t); });
      if (e.tema) p.set("tema", e.tema);
      if (e.municipio) p.set("municipio", e.municipio);
      if (e.evidencia) p.set("evidencia", String(e.evidencia));
      if (e.ordem !== "relevancia") p.set("ordem", e.ordem);
      var qs = p.toString();
      window.history.replaceState(null, "", window.location.pathname + (qs ? "?" + qs : ""));
    }

    function pintarTags(e) {
      if (!tagsAplicadas) return;
      var itens = [];
      function tag(rotulo, acao, alvo) {
        itens.push({ rotulo: rotulo, acao: acao, alvo: alvo });
      }
      if (e.q) tag('Texto: "' + campoTexto.value.trim() + '"', function () { campoTexto.value = ""; }, campoTexto);
      e.tipos.forEach(function (t) {
        var caixa = caixasTipo.filter(function (c) { return c.value === t; })[0];
        if (caixa) tag(caixa.parentNode.textContent.trim(), function () { caixa.checked = false; }, caixa);
      });
      if (e.tema) tag(campoTema.options[campoTema.selectedIndex].text, function () { campoTema.value = ""; }, campoTema);
      if (e.municipio) tag(campoMunicipio.options[campoMunicipio.selectedIndex].text, function () { campoMunicipio.value = ""; }, campoMunicipio);
      if (e.evidencia) tag("Evidência ≥ " + e.evidencia, function () { campoEvidencia.value = "0"; }, campoEvidencia);

      if (!itens.length) { tagsAplicadas.innerHTML = ""; return; }
      tagsAplicadas.innerHTML = itens.map(function (it, i) {
        return '<li class="filtro-tag">' + escapa(it.rotulo) +
          '<button type="button" data-tag="' + i + '" aria-label="Remover filtro ' + escapa(it.rotulo) + '">✕</button></li>';
      }).join("");
      $$("button", tagsAplicadas).forEach(function (b) {
        b.addEventListener("click", function () {
          itens[parseInt(b.getAttribute("data-tag"), 10)].acao();
          aplicar();
        });
      });
    }

    function aplicar() {
      var e = estado();
      var resultados = cartoes.filter(function (c) { return combina(c, e); });
      resultados.sort(function (a, b) { return ordenar(a, b, e.ordem); });

      cartoes.forEach(function (c) { c.hidden = true; });
      resultados.forEach(function (c, i) {
        c.hidden = i >= visiveis;
        grade.appendChild(c);   // reordena no DOM
      });

      var mostrando = Math.min(visiveis, resultados.length);
      if (saida) {
        saida.innerHTML = resultados.length
          ? "Mostrando <b>" + mostrando + "</b> de <b>" + resultados.length + "</b> registro" +
            (resultados.length === 1 ? "" : "s") + " — de " + cartoes.length + " no acervo."
          : "Nenhum registro corresponde aos filtros escolhidos.";
      }
      if (aviso) aviso.hidden = resultados.length !== 0;
      if (botaoMais) {
        var faltam = resultados.length - mostrando;
        botaoMais.hidden = faltam <= 0;
        var rotulo = $("span", botaoMais);
        if (rotulo) rotulo.textContent = "Mostrar mais " + Math.min(PASSO, faltam) + " registro" + (faltam === 1 ? "" : "s");
      }
      pintarTags(e);
      sincronizarUrl(e);
    }

    function lerUrl() {
      var p = new URLSearchParams(window.location.search);
      if (campoTexto && p.get("q")) campoTexto.value = p.get("q");
      var tipos = p.getAll("tipo");
      caixasTipo.forEach(function (c) { c.checked = tipos.indexOf(c.value) !== -1; });
      if (campoTema && p.get("tema")) campoTema.value = p.get("tema");
      if (campoMunicipio && p.get("municipio")) campoMunicipio.value = p.get("municipio");
      if (campoEvidencia && p.get("evidencia")) campoEvidencia.value = p.get("evidencia");
      if (campoOrdem && p.get("ordem")) campoOrdem.value = p.get("ordem");
    }

    // ligações
    [campoTexto].forEach(function (el) {
      if (!el) return;
      var timer = null;
      el.addEventListener("input", function () {
        window.clearTimeout(timer);
        timer = window.setTimeout(function () { visiveis = PASSO; aplicar(); }, 140);
      });
    });
    [campoTema, campoMunicipio, campoEvidencia, campoOrdem].forEach(function (el) {
      if (el) el.addEventListener("change", function () { visiveis = PASSO; aplicar(); });
    });
    caixasTipo.forEach(function (c) { c.addEventListener("change", function () { visiveis = PASSO; aplicar(); }); });

    if (botaoMais) {
      botaoMais.addEventListener("click", function () { visiveis += PASSO; aplicar(); });
    }
    function limparTudo() {
      if (campoTexto) campoTexto.value = "";
      if (campoTema) campoTema.value = "";
      if (campoMunicipio) campoMunicipio.value = "";
      if (campoEvidencia) campoEvidencia.value = "0";
      if (campoOrdem) campoOrdem.value = "relevancia";
      caixasTipo.forEach(function (c) { c.checked = false; });
      visiveis = PASSO;
      aplicar();
      anuncia("Filtros limpos. Todos os registros estão visíveis.");
    }
    // dois gatilhos para a mesma ação: o da barra de filtros e o do estado vazio
    ["#limpar-filtros", "#limpar-filtros-2"].forEach(function (sel) {
      var b = $(sel);
      if (b) b.addEventListener("click", limparTudo);
    });

    // densidade da lista (preferência persistida)
    $$("[data-densidade]").forEach(function (b) {
      b.addEventListener("click", function () {
        var modo = b.getAttribute("data-densidade");
        grade.classList.toggle("densa", modo === "densa");
        $$("[data-densidade]").forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
        guardar("wi-densidade", modo);
      });
    });
    if (ler("wi-densidade") === "densa") {
      grade.classList.add("densa");
      $$("[data-densidade]").forEach(function (o) {
        o.setAttribute("aria-pressed", String(o.getAttribute("data-densidade") === "densa"));
      });
    }

    lerUrl();
    aplicar();
  }

  /* ================================================================
     BUSCA — instantânea, com realce, teclado e histórico
     ================================================================ */
  function moduloBusca() {
    var fonte = $("#dados-busca");
    var campo = $("#campo-busca");
    var saida = $("#resultados");
    if (!fonte || !campo || !saida) return;

    var dados;
    try { dados = JSON.parse(fonte.textContent); } catch (e) { return; }

    var limpar = $("#limpar-busca");
    var contador = $("#conta-resultados");
    var recentes = $("#buscas-recentes");
    var CHAVE = "wi-buscas";
    var selecao = -1;
    var timer = null;
    var ultimoTermo = "";

    function historico() {
      try { return JSON.parse(ler(CHAVE) || "[]"); } catch (e) { return []; }
    }
    function salvarHistorico(termo) {
      var t = termo.trim();
      if (t.length < 3) return;
      var lista = historico().filter(function (x) { return x !== t; });
      lista.unshift(t);
      guardar(CHAVE, JSON.stringify(lista.slice(0, 6)));
    }
    function pintarRecentes() {
      if (!recentes) return;
      var lista = historico();
      if (!lista.length) { recentes.hidden = true; recentes.innerHTML = ""; return; }
      recentes.hidden = false;
      recentes.innerHTML = '<span class="sr-only">Buscas recentes:</span>' + lista.map(function (t) {
        return '<a class="chip" href="' + escapa(window.location.pathname) + '?q=' + encodeURIComponent(t) +
          '" data-recente="' + escapa(t) + '">' + escapa(t) + "</a>";
      }).join(" ");
      $$("[data-recente]", recentes).forEach(function (a) {
        a.addEventListener("click", function (e) {
          e.preventDefault();
          campo.value = a.getAttribute("data-recente");
          render(campo.value);
          campo.focus();
        });
      });
    }

    function categorias(resultados) {
      var mapa = {};
      resultados.forEach(function (r) { mapa[r.item.cat] = (mapa[r.item.cat] || 0) + 1; });
      return Object.keys(mapa).map(function (c) { return { nome: c, n: mapa[c] }; });
    }

    function render(termo) {
      var bruto = String(termo || "").trim();
      ultimoTermo = bruto;
      if (limpar) limpar.classList.toggle("visivel", bruto.length > 0);
      var termos = normalizar(bruto).split(/\s+/).filter(Boolean);

      if (termos.length === 0 || normalizar(bruto).length < 2) {
        saida.innerHTML =
          '<div class="estado estado-vazio"><p class="estado-titulo">Comece a digitar para buscar no acervo</p>' +
          "<p>O índice cobre " + dados.length + " itens: realizações, temas, municípios, dossiês, marcos da linha do tempo e clipping.</p>" +
          '<p class="busca-atalhos">Sugestões: <a href="?q=JUCESP">JUCESP</a> · <a href="?q=Cadastro+Positivo">Cadastro Positivo</a> · ' +
          '<a href="?q=Mar%C3%ADlia">Marília</a> · <a href="?q=microempresas">microempresas</a> · ' +
          '<a href="?q=Jap%C3%A3o">Japão</a> · <a href="?q=desburocratiza%C3%A7%C3%A3o">desburocratização</a></p></div>';
        if (contador) contador.innerHTML = "";
        pintarRecentes();
        if (recentes) recentes.hidden = historico().length === 0;
        return;
      }

      var achados = [];
      dados.forEach(function (item) {
        var alvo = normalizar(item.ch + " " + item.t + " " + item.d);
        var pontos = 0;
        var titulo = normalizar(item.t);
        termos.forEach(function (p) {
          if (alvo.indexOf(p) === -1) { pontos = -999; }
          else if (titulo.indexOf(p) !== -1) { pontos += 3; }
          else { pontos += 1; }
        });
        if (pontos > 0) achados.push({ pontos: pontos, item: item });
      });
      achados.sort(function (a, b) { return b.pontos - a.pontos || a.item.t.localeCompare(b.item.t, "pt-BR"); });

      if (contador) {
        contador.innerHTML = achados.length
          ? "<b>" + achados.length + "</b> resultado" + (achados.length === 1 ? "" : "s") + ' para <b>"' + escapa(bruto) + '"</b>'
          : "";
      }
      if (recentes) recentes.hidden = true;

      if (!achados.length) {
        saida.innerHTML =
          '<div class="estado estado-vazio"><p class="estado-titulo">Nada encontrado para "' + escapa(bruto) + '"</p>' +
          "<p>Este acervo publica apenas o que tem fonte. Pode ser que o registro ainda não exista, ou que o termo usado seja outro.</p>" +
          '<div class="estado-acoes">' +
          '<a class="btn btn-fantasma" href="' + escapa(window.location.pathname) + '">Limpar busca</a>' +
          '<a class="btn" href="' + escapa(caminhoBase() + "/realizacoes/") + '">Ver todas as realizações</a>' +
          '<a class="btn btn-fantasma" href="' + escapa(caminhoBase() + "/fontes/") + '">Como o acervo é construído</a>' +
          "</div></div>";
        anuncia("Nenhum resultado para " + bruto);
        return;
      }

      var cats = categorias(achados).sort(function (a, b) { return b.n - a.n; });
      var chips = cats.map(function (c) {
        return '<button type="button" class="chip" data-cat="' + escapa(c.nome) + '" aria-pressed="false">' +
          escapa(c.nome) + " (" + c.n + ")</button>";
      }).join("");

      function lista(itens) {
        return '<div class="grade">' + itens.map(function (par, i) {
          var it = par.item;
          return '<article class="card" data-cat="' + escapa(it.cat) + '">' +
            '<div class="card-tags"><span class="tag-tipo">' + escapa(it.cat) + "</span></div>" +
            '<h3><a href="' + escapa(it.u) + '" data-pos="' + i + '">' + realca(it.t, termos) + "</a></h3>" +
            "<p>" + realca(it.d, termos) + "</p></article>";
        }).join("") + "</div>";
      }

      saida.innerHTML = (cats.length > 1 ? '<div class="busca-categorias" role="group" aria-label="Filtrar resultados por tipo">' + chips + "</div>" : "") +
        lista(achados.slice(0, 60)) +
        (achados.length > 60 ? '<p class="dica">Exibindo os 60 mais relevantes. Refine a busca para ver os demais.</p>' : "");

      $$("[data-cat]", saida).forEach(function (b) {
        b.addEventListener("click", function () {
          var ativo = b.getAttribute("aria-pressed") === "true";
          $$("[data-cat]", saida).forEach(function (o) { o.setAttribute("aria-pressed", "false"); });
          b.setAttribute("aria-pressed", String(!ativo));
          var cat = b.getAttribute("data-cat");
          var filtrados = ativo ? achados : achados.filter(function (p) { return p.item.cat === cat; });
          var alvo = $(".grade", saida);
          if (alvo) alvo.outerHTML = lista(filtrados.slice(0, 60));
          ligarResultados();
          anuncia((ativo ? achados.length : filtrados.length) + " resultados exibidos.");
        });
      });
      ligarResultados();
      anuncia(achados.length + " resultados para " + bruto);
    }

    function ligarResultados() {
      selecao = -1;
      $$(".grade .card a", saida).forEach(function (a) {
        a.addEventListener("click", function () { salvarHistorico(ultimoTermo); });
      });
    }

    function caminhoBase() {
      return window.location.pathname.replace(/\/busca\/?$/, "");
    }

    function mover(delta) {
      var links = $$(".grade .card a", saida);
      if (!links.length) return;
      selecao = (selecao + delta + links.length) % links.length;
      links.forEach(function (a, i) { a.parentNode.parentNode.classList.toggle("foco-busca", i === selecao); });
      links[selecao].focus();
    }

    campo.addEventListener("input", function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { render(campo.value); }, 130);
    });
    campo.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); mover(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); mover(-1); }
      else if (e.key === "Escape") { campo.value = ""; render(""); }
      else if (e.key === "Enter") {
        e.preventDefault();
        var links = $$(".grade .card a", saida);
        var alvo = links[selecao] || links[0];
        if (alvo) { salvarHistorico(ultimoTermo); window.location.href = alvo.getAttribute("href"); }
      }
    });
    if (limpar) {
      limpar.addEventListener("click", function () {
        campo.value = "";
        render("");
        campo.focus();
      });
    }

    var inicial = new URLSearchParams(window.location.search).get("q");
    if (inicial) { campo.value = inicial; render(inicial); campo.focus(); campo.setSelectionRange(inicial.length, inicial.length); }
    else { render(""); }
  }

  /* ================================================================
     LINHA DO TEMPO — filtro por período
     ================================================================ */
  function moduloAnos() {
    var painel = $("#filtro-anos");
    var itens = $$(".tl-item[data-ano]");
    if (!painel || !itens.length) return;
    var saida = $("#anos-contagem");

    function aplicar( decada ) {
      var n = 0;
      itens.forEach(function (li) {
        var ano = parseInt(li.getAttribute("data-ano"), 10);
        var ok = !decada || (ano >= decada && ano < decada + 10);
        li.hidden = !ok;
        if (ok) n++;
      });
      $$("button", painel).forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-decada") === String(decada || "")));
      });
      if (saida) saida.innerHTML = "<b>" + n + "</b> marco" + (n === 1 ? "" : "s") + " exibido" + (n === 1 ? "" : "s") + ".";
    }
    $$("button", painel).forEach(function (b) {
      b.addEventListener("click", function () { aplicar(parseInt(b.getAttribute("data-decada"), 10) || 0); });
    });
    aplicar(0);
  }

  /* ================================================================
     CLIPPING — filtro por texto e por tipo de fonte
     ================================================================ */
  function moduloClipping() {
    var painel = $("#filtros-clipping");
    if (!painel) return;
    var itens = $$(".clip-item[data-fonte]");
    var campo = $("#clip-texto");
    var oficiais = $("#clip-oficiais");
    var saida = $("#clip-contagem");

    function aplicar() {
      var q = normalizar((campo && campo.value) || "");
      var soOficiais = oficiais && oficiais.checked;
      var n = 0;
      itens.forEach(function (li) {
        var ok = true;
        if (q && normalizar(li.getAttribute("data-texto")).indexOf(q) === -1) ok = false;
        if (soOficiais && li.getAttribute("data-oficial") !== "1") ok = false;
        li.hidden = !ok;
        if (ok) n++;
      });
      $$(".clip-dia").forEach(function (sec) {
        var visiveis = $$(".clip-item:not([hidden])", sec).length;
        sec.hidden = visiveis === 0;
        var conta = $(".conta", sec);
        if (conta) conta.textContent = "(" + visiveis + ")";
      });
      if (saida) saida.innerHTML = "<b>" + n + "</b> de <b>" + itens.length + "</b> menções.";
      var aviso = $("#clip-aviso");
      if (aviso) aviso.hidden = n !== 0;
    }
    if (campo) campo.addEventListener("input", aplicar);
    if (oficiais) oficiais.addEventListener("change", aplicar);
    aplicar();
  }

  /* ================================================================
     ATALHOS DE TECLADO
     ================================================================ */
  function moduloAtalhos() {
    doc.addEventListener("keydown", function (e) {
      var alvo = e.target;
      var digitando = alvo && /^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName);
      if ((e.key === "/" && !digitando && !e.metaKey && !e.ctrlKey) ||
          ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K"))) {
        var campo = $("#campo-busca");
        if (!campo && window.location.pathname.indexOf("/busca") === -1) {
          window.location.href = ($(".util-busca") || {}).href || "busca/";
          e.preventDefault();
          return;
        }
        if (campo) { e.preventDefault(); campo.focus(); campo.select(); }
      }
    });
  }

  /* ---------- inicialização ---------- */
  function iniciar() {
    root.classList.remove("sem-js");
    root.classList.add("com-js");
    rodar("tema", moduloTema);
    rodar("menu", moduloMenu);
    rodar("nav", moduloNav);
    rodar("leitura", moduloLeitura);
    rodar("sumario", moduloSumario);
    rodar("copiar", moduloCopiar);
    rodar("filtros", moduloFiltros);
    rodar("busca", moduloBusca);
    rodar("anos", moduloAnos);
    rodar("clipping", moduloClipping);
    rodar("atalhos", moduloAtalhos);
  }

  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
