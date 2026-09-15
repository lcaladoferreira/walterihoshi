/* Verificação opcional de interação — exige Node.js e jsdom (ferramenta de
   desenvolvimento; o site publicado continua sem nenhuma dependência).

   Instalação e uso:
       npm install jsdom            # ou: npm install --no-save jsdom
       python3 scripts/gerar.py
       node scripts/testar_ux_interacoes.js

   Exercita o static/app.js REAL contra o HTML REAL de public/ dentro do jsdom.
   Não reimplementa lógica nenhuma: carrega os artefatos do build.

   Detalhe que importa: app.js se inicializa em DOMContentLoaded. Toda asserção
   acontece depois de pronto(), que espera o módulo marcar <html class="com-js">.
   Assertar antes disso mede o harness, não o site. */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");
const { VirtualConsole } = require("jsdom");

const RAIZ = path.join(__dirname, "..");
const PUBLIC = path.join(RAIZ, "public");
const APP = fs.readFileSync(path.join(RAIZ, "static", "app.js"), "utf8");

let falhas = 0;
function ok(nome, cond, extra) {
  console.log((cond ? "  ok    " : "  FALHA ") + nome + (extra ? " → " + extra : ""));
  if (!cond) falhas++;
}
const espera = ms => new Promise(r => setTimeout(r, ms));

async function carregar(rel) {
  const html = fs.readFileSync(path.join(PUBLIC, rel), "utf8");
  const erros = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => erros.push(e.message));
  vc.on("error", (...a) => erros.push(a.join(" ")));
  const dom = new JSDOM(html, {
    url: "https://exemplo.test/walterihoshi/" + rel,
    runScripts: "dangerously",
    pretendToBeVisual: true,
    virtualConsole: vc,
  });
  dom.window.eval(APP);
  // espera a inicialização de verdade
  for (let i = 0; i < 100 && !dom.window.document.documentElement.classList.contains("com-js"); i++) {
    await espera(10);
  }
  if (!dom.window.document.documentElement.classList.contains("com-js")) {
    throw new Error("app.js não inicializou em " + rel + " — erros: " + erros.join(" | "));
  }
  dom.erros = erros;
  return dom;
}

const visiveis = (doc, sel) => [...doc.querySelectorAll(sel)].filter(el => !el.hidden);
const fogo = (window, el, tipo) => el.dispatchEvent(new window.Event(tipo, { bubbles: true }));

(async function () {
  console.log("== /realizacoes/ : facetas ==");
  {
    const dom = await carregar("realizacoes/index.html");
    const { window } = dom, doc = window.document;
    const total = doc.querySelectorAll(".card[data-id]").length;
    ok("todos os registros chegam no HTML", total === 26, total + " cartões");
    ok("revelação progressiva: 12 visíveis no início", visiveis(doc, ".card[data-id]").length === 12,
      visiveis(doc, ".card[data-id]").length + " visíveis");
    ok("contagem anunciada", /Mostrando/.test(doc.querySelector("#filtro-contagem").textContent),
      doc.querySelector("#filtro-contagem").textContent.trim());
    ok("estado vazio começa escondido", doc.querySelector("#filtro-aviso").hidden);
    ok("nenhum erro de JS na página", dom.erros.length === 0, dom.erros.join(" | "));

    const q = doc.querySelector("#f-texto");
    q.value = "jucesp"; fogo(window, q, "input"); await espera(260);
    const n1 = visiveis(doc, ".card[data-id]").length;
    ok("filtro por texto reduz a lista", n1 > 0 && n1 < total, n1 + " resultados para 'jucesp'");
    ok("estado dos filtros vai para a URL", window.location.search.includes("q=jucesp"), window.location.search);
    ok("filtro aplicado aparece como etiqueta removível",
      doc.querySelector("#filtros-aplicados").textContent.includes("jucesp"));

    const caixa = doc.querySelector('input[name="tipo"][value="LEI"]');
    caixa.checked = true; fogo(window, caixa, "change"); await espera(80);
    ok("facetas combinam (E, não OU)", visiveis(doc, ".card[data-id]").length === 0);
    ok("combinação impossível → estado vazio visível", !doc.querySelector("#filtro-aviso").hidden);
    ok("estado vazio oferece ação de recuperação", !!doc.querySelector("#limpar-filtros-2"));

    doc.querySelector("#limpar-filtros").dispatchEvent(new window.Event("click", { bubbles: true }));
    await espera(80);
    ok("limpar filtros restaura a lista", visiveis(doc, ".card[data-id]").length === 12);
    ok("limpar filtros limpa a URL", window.location.search === "", "'" + window.location.search + "'");
    ok("limpar filtros esconde o estado vazio", doc.querySelector("#filtro-aviso").hidden);

    const ordem = doc.querySelector("#f-ordem");
    ordem.value = "titulo"; fogo(window, ordem, "change"); await espera(80);
    const titulos = visiveis(doc, ".card[data-id]").map(c => c.getAttribute("data-titulo"));
    ok("ordenação A–Z reordena o DOM de verdade",
      JSON.stringify(titulos) === JSON.stringify([...titulos].sort((a, b) => a.localeCompare(b, "pt-BR"))),
      "primeiro: " + titulos[0]);

    ordem.value = "evidencia"; fogo(window, ordem, "change"); await espera(80);
    const evs = visiveis(doc, ".card[data-id]").map(c => +c.getAttribute("data-ev"));
    ok("ordenação por evidência é decrescente", evs.every((v, i) => i === 0 || evs[i - 1] >= v), evs.join(","));

    ordem.value = "relevancia"; fogo(window, ordem, "change"); await espera(80);
    doc.querySelector("#carregar-mais").dispatchEvent(new window.Event("click", { bubbles: true }));
    await espera(80);
    ok("'mostrar mais' revela o lote seguinte", visiveis(doc, ".card[data-id]").length === 24,
      visiveis(doc, ".card[data-id]").length + " visíveis");
    doc.querySelector("#carregar-mais").dispatchEvent(new window.Event("click", { bubbles: true }));
    await espera(80);
    ok("no fim da lista o botão some", doc.querySelector("#carregar-mais").hidden);

    doc.querySelector('[data-densidade="densa"]').dispatchEvent(new window.Event("click", { bubbles: true }));
    ok("densidade alterna", doc.querySelector("#lista-registros .grade").classList.contains("densa"));
    ok("densidade persiste", window.localStorage.getItem("wi-densidade") === "densa");
  }

  console.log("== /busca/ : busca instantânea ==");
  {
    const dom = await carregar("busca/index.html");
    const { window } = dom, doc = window.document;
    ok("estado inicial orienta antes de digitar", /Comece a digitar/.test(doc.querySelector("#resultados").textContent));
    ok("estado inicial traz sugestões clicáveis", doc.querySelectorAll("#resultados .busca-atalhos a").length >= 5);
    ok("nenhum erro de JS na página", dom.erros.length === 0, dom.erros.join(" | "));

    const campo = doc.querySelector("#campo-busca");
    campo.value = "marília"; fogo(window, campo, "input"); await espera(260);
    const cards = doc.querySelectorAll("#resultados .card");
    ok("busca com acento encontra (normalização)", cards.length > 0, cards.length + " resultados para 'marília'");
    ok("termo vem realçado com <mark>", doc.querySelectorAll("#resultados mark").length > 0,
      doc.querySelectorAll("#resultados mark").length + " realces");
    ok("contador diz quantos achou", /resultado/.test(doc.querySelector("#conta-resultados").textContent),
      doc.querySelector("#conta-resultados").textContent.trim());
    ok("botão limpar aparece", doc.querySelector("#limpar-busca").classList.contains("visivel"));

    campo.value = "zzzzinexistente"; fogo(window, campo, "input"); await espera(260);
    ok("busca vazia → estado vazio com saídas",
      /Nada encontrado/.test(doc.querySelector("#resultados").textContent) &&
      doc.querySelectorAll("#resultados .estado-acoes a").length >= 2);

    campo.value = "jucesp"; fogo(window, campo, "input"); await espera(260);
    const chips = doc.querySelectorAll("#resultados .busca-categorias [data-cat]");
    ok("resultados agrupam por tipo de conteúdo", chips.length >= 2, chips.length + " categorias");
    const antes = doc.querySelectorAll("#resultados .card").length;
    chips[0].dispatchEvent(new window.Event("click", { bubbles: true })); await espera(80);
    const depois = doc.querySelectorAll("#resultados .card").length;
    ok("clicar na categoria refina a lista", depois < antes, antes + " → " + depois);

    doc.querySelector("#limpar-busca").dispatchEvent(new window.Event("click", { bubbles: true }));
    await espera(80);
    ok("limpar volta ao estado inicial", campo.value === "" && /Comece a digitar/.test(doc.querySelector("#resultados").textContent));
  }

  console.log("== registro : compartilhar e navegação ==");
  {
    const dom = await carregar("realizacoes/nomeacao-jucesp/index.html");
    const { window } = dom, doc = window.document;
    ok("nenhum erro de JS na página", dom.erros.length === 0, dom.erros.join(" | "));

    const copiar = doc.querySelector(".copiar");
    copiar.dispatchEvent(new window.Event("click", { bubbles: true })); await espera(120);
    ok("copiar link dá retorno visível (jsdom não tem clipboard → rota de fallback)",
      copiar.textContent.includes("http") || /copiado/i.test(copiar.textContent), copiar.textContent.trim().slice(0, 50));
    ok("retorno é anunciado para leitor de tela", doc.querySelector("#avisos").textContent.trim().length > 0,
      doc.querySelector("#avisos").textContent.trim().slice(0, 60));

    const nav = doc.querySelector(".anterior-proximo");
    ok("registro tem anterior/próximo", !!nav && nav.querySelectorAll("a").length >= 1,
      nav ? nav.querySelectorAll("a").length + " link(s)" : "ausente");
    ok("registro tem sumário", doc.querySelectorAll(".sumario a").length >= 3,
      doc.querySelectorAll(".sumario a").length + " seções no índice");
  }

  console.log("== chrome global : tema, menu, grupos ==");
  {
    const dom = await carregar("fontes/index.html");
    const { window } = dom, doc = window.document;
    const botao = doc.querySelector("#alternar-tema");
    const seq = [];
    for (let i = 0; i < 3; i++) {
      botao.dispatchEvent(new window.Event("click", { bubbles: true }));
      seq.push(doc.documentElement.getAttribute("data-tema"));
    }
    ok("tema alterna claro → escuro → automático", JSON.stringify(seq) === '["claro","escuro","auto"]', seq.join(" → "));
    ok("preferência de tema persiste", window.localStorage.getItem("wi-tema") === "auto");
    ok("botão de tema descreve o estado atual", /automático/.test(botao.getAttribute("aria-label")),
      botao.getAttribute("aria-label"));

    const abrir = doc.querySelector("#abrir-menu");
    abrir.dispatchEvent(new window.Event("click", { bubbles: true }));
    ok("menu abre e declara estado", doc.body.classList.contains("menu-aberto") && abrir.getAttribute("aria-expanded") === "true");
    ok("menu abre o drawer", doc.querySelector("#menu-lateral").getAttribute("aria-hidden") === "false");
    ok("scroll trava com o menu aberto", doc.body.classList.contains("menu-aberto"));
    doc.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    ok("Esc fecha o menu", !doc.body.classList.contains("menu-aberto") && abrir.getAttribute("aria-expanded") === "false");

    const grupo = doc.querySelector("details.nav-grupo");
    grupo.open = true;
    doc.body.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    ok("menu revelável fecha ao clicar fora", grupo.open === false);
    ok("item atual marcado com aria-current", !!doc.querySelector('[aria-current="page"]'));
  }

  console.log("== linha do tempo e clipping ==");
  {
    const dom = await carregar("linha-do-tempo/index.html");
    const { window } = dom, doc = window.document;
    const total = doc.querySelectorAll(".tl-item").length;
    const botao = [...doc.querySelectorAll("#filtro-anos button")].find(b => b.getAttribute("data-decada") === "2000");
    botao.dispatchEvent(new window.Event("click", { bubbles: true }));
    const n = visiveis(doc, ".tl-item").length;
    ok("filtro por década funciona", n > 0 && n < total, total + " → " + n + " marcos nos anos 2000");
    ok("todos os visíveis são da década", visiveis(doc, ".tl-item")
      .every(li => li.getAttribute("data-ano").startsWith("200")));
    ok("contagem atualizada", /\d+ marco/.test(doc.querySelector("#anos-contagem").textContent),
      doc.querySelector("#anos-contagem").textContent.trim());
    ok("botão ativo marcado", botao.getAttribute("aria-pressed") === "true");
  }
  {
    const dom = await carregar("clipping/index.html");
    const { window } = dom, doc = window.document;
    const total = doc.querySelectorAll(".clip-item").length;
    const alvo = doc.querySelector(".clip-item").getAttribute("data-fonte");
    const campo = doc.querySelector("#clip-texto");
    campo.value = alvo; fogo(window, campo, "input"); await espera(80);
    const n = visiveis(doc, ".clip-item").length;
    ok("filtro por veículo funciona", n > 0 && n < total, total + " → " + n + " para '" + alvo + "'");
    ok("dias sem resultado são ocultados",
      [...doc.querySelectorAll(".clip-dia")].some(s => s.hidden));

    campo.value = ""; fogo(window, campo, "input");
    const oficiais = doc.querySelector("#clip-oficiais");
    oficiais.checked = true; fogo(window, oficiais, "change"); await espera(80);
    const resto = visiveis(doc, ".clip-item");
    ok("filtro por nível de fonte respeita o critério",
      resto.every(li => li.getAttribute("data-oficial") === "1"), resto.length + " menções");
    ok("resultado zero mostra aviso explicativo (não tela em branco)",
      resto.length > 0 || !doc.querySelector("#clip-aviso").hidden,
      resto.length + " menções oficiais nesta versão");
  }

  console.log("-".repeat(72));
  console.log(falhas ? falhas + " FALHAS" : "todas as interações passaram");
  process.exit(falhas ? 1 : 0);
})().catch(e => { console.error("ERRO NO HARNESS:", e.message); process.exit(2); });
