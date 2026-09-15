/* Medição de responsividade — ferramenta opcional de desenvolvimento.

   Exige Node.js e Playwright (com um Chromium instalado). O site publicado
   continua sem nenhuma dependência de runtime.

   Instalação e uso:
       npm install playwright && npx playwright install chromium
       python3 scripts/gerar.py
       node scripts/medir_responsividade.js

   Em contêiner onde o Chromium já existe, aponte para ele e evite o download:
       CHROMIUM_PATH=/usr/bin/chromium node scripts/medir_responsividade.js

   Por que existe: as checagens de scripts/testar_ux.py leem o HTML/CSS e
   garantem que o *padrão* está certo (grade com min(), tabela dentro do bloco
   rolável, alvos de 44px). Só um navegador de verdade sabe se, no layout final,
   a página rola para o lado em 320px, se um rótulo longo estoura a viewport ou
   se um alvo de toque ficou pequeno. Este script faz essa medição no build real
   — não numa reimplementação — e sai com código 1 quando encontra problema.

   O que ele considera defeito (FALHA, sai com código 1):
     1. rolagem horizontal na página (document.scrollWidth > clientWidth);
     2. elemento visível ultrapassando a viewport sem um ancestral que contenha
        a rolagem (a rolagem tem de ficar no bloco, não na página);
     3. conteúdo cortado por overflow escondido;
     4. controle (botão, campo, resumo, select) menor que 24px em qualquer lado
        — piso da WCAG 2.5.8, ou seja, violação de nível AA.

   E o que ele reporta como AVISO (não quebra o build):
     5. controle entre 24px e 44px — abaixo do alvo confortável que o projeto
        declara (--alvo: 44px), mas ainda conforme;
     6. link de texto no meio de uma frase — exceção explícita da WCAG 2.5.8,
        e que já é alcançável pelo teclado.
*/
const fs = require("fs");
const http = require("http");
const path = require("path");

const RAIZ = path.join(__dirname, "..");
const PUBLIC = path.join(RAIZ, "public");
const CONFIG = JSON.parse(fs.readFileSync(path.join(RAIZ, "data", "config.json"), "utf8"));
const BASE = (CONFIG.base_path || "").replace(/\/$/, "");

const VIEWPORTS = [
  [280, 700, "280 (dobrável fechado)"],
  [320, 720, "320 (menor comum)"],
  [360, 740, "360 (Android)"],
  [390, 844, "390 (iPhone)"],
  [414, 896, "414 (iPhone grande)"],
  [768, 1024, "768 (tablet)"],
  [1024, 768, "1024 (tablet paisagem)"],
  [1280, 800, "1280 (desktop)"],
  [1440, 900, "1440 (desktop largo)"],
];

const PAGINAS = [
  ["/", "home"],
  ["/realizacoes/", "realizacoes"],
  ["/temas/", "temas"],
  ["/municipios/", "municipios"],
  ["/linha-do-tempo/", "linha-do-tempo"],
  ["/mandatos/", "mandatos"],
  ["/jucesp/", "jucesp"],
  ["/convenios/", "convenios"],
  ["/comunidade-nikkei/", "comunidade-nikkei"],
  ["/fontes/", "fontes"],
  ["/clipping/", "clipping"],
  ["/atualizacoes/", "atualizacoes"],
  ["/busca/?q=marilia", "busca"],
  ["/404.html", "404"],
];

const MEDICAO = () => {
  const largura = document.documentElement.clientWidth;
  const out = { pagina: document.documentElement.scrollWidth, estouros: [], cortados: [], alvos: [] };

  const visivel = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return false;
    const det = el.closest("details");
    if (det && !det.open && !el.matches("summary")) return false; // fechado não é pintado
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const nome = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    else if (typeof el.className === "string" && el.className.trim()) s += "." + el.className.trim().split(/\s+/).join(".");
    return s;
  };

  // 2. estouro da viewport (ignorando o que está dentro de um bloco rolável)
  const contido = (el) => {
    let p = el.parentElement;
    while (p) {
      if (/(auto|scroll|hidden|clip)/.test(getComputedStyle(p).overflowX)) return true;
      p = p.parentElement;
    }
    return false;
  };
  for (const el of document.querySelectorAll("body *")) {
    if (!visivel(el) || contido(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > largura + 1 || r.left < -1) {
      out.estouros.push({ el: nome(el), dir: Math.round(r.right), texto: (el.textContent || "").trim().slice(0, 50) });
    }
  }

  // 3. conteúdo cortado (só quando algum filho real ultrapassa a caixa)
  for (const el of document.querySelectorAll("body *")) {
    if (!visivel(el)) continue;
    if (!/hidden|clip/.test(getComputedStyle(el).overflowX)) continue;
    if (el.scrollWidth <= el.clientWidth + 2 || el.clientWidth === 0) continue;
    const caixa = el.getBoundingClientRect().right;
    if (![...el.children].some((f) => f.getBoundingClientRect().right > caixa + 1)) continue;
    out.cortados.push({ el: nome(el), conteudo: el.scrollWidth, caixa: el.clientWidth,
                        texto: (el.textContent || "").trim().slice(0, 50) });
  }

  // 4. alvos de toque — separando controle de link no meio de frase
  const CONTROLE = 'button, input, select, summary, [role="button"]';
  for (const el of document.querySelectorAll('a[href], button, input, select, summary, [role="button"]')) {
    if (!visivel(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width >= 44 && r.height >= 44) continue;
    const cs = getComputedStyle(el);
    const ehControle = el.matches(CONTROLE);
    // link de texto (inline, dentro de um bloco de leitura ou frase solta):
    // exceção da WCAG 2.5.8 — não é defeito nem aviso
    if (!ehControle && (cs.display === "inline" || cs.display === "")) continue;
    const menor = Math.min(r.width, r.height);
    out.alvos.push({ el: nome(el), w: Math.round(r.width), h: Math.round(r.height), menor,
                     grave: ehControle && menor < 24,
                     rotulo: (el.textContent || el.getAttribute("aria-label") || "").trim().slice(0, 40) });
  }
  return out;
};

function servir() {
  const server = http.createServer((req, res) => {
    let rel = decodeURIComponent(req.url.split("?")[0]);
    if (BASE && rel.startsWith(BASE)) rel = rel.slice(BASE.length) || "/";
    if (rel.endsWith("/")) rel += "index.html";
    const arq = path.join(PUBLIC, rel.replace(/^\/+/, ""));
    if (!arq.startsWith(PUBLIC) || !fs.existsSync(arq) || fs.statSync(arq).isDirectory()) {
      res.writeHead(404, { "content-type": "text/plain" });
      return res.end("não encontrado");
    }
    const tipos = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                    ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png" };
    res.writeHead(200, { "content-type": tipos[path.extname(arq)] || "application/octet-stream" });
    res.end(fs.readFileSync(arq));
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

(async () => {
  let chromium;
  try {
    ({ chromium } = require("playwright"));
  } catch (e) {
    console.error("Playwright não está instalado.\n" +
      "  npm install playwright && npx playwright install chromium\n" +
      "Sem ele, rode as checagens estáticas: python3 scripts/testar_ux.py");
    process.exit(2);
  }
  if (!fs.existsSync(path.join(PUBLIC, "index.html"))) {
    console.error("public/ não existe. Rode antes: python3 scripts/gerar.py");
    process.exit(2);
  }

  const server = await servir();
  const porta = server.address().port;
  let browser;
  try {
    browser = await chromium.launch({
      executablePath: process.env.CHROMIUM_PATH || undefined,
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
  } catch (e) {
    server.close();
    console.error("Não consegui abrir o Chromium: " + e.message.split("\n")[0] + "\n" +
      "  Instale com: npx playwright install chromium\n" +
      "  Ou aponte um já instalado: CHROMIUM_PATH=/caminho/do/chrome node scripts/medir_responsividade.js");
    process.exit(2);
  }
  const problemas = [];
  const avisos = new Map();
  let medidos = 0;

  for (const [w, h, rotulo] of VIEWPORTS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    for (const [rota, nomePagina] of PAGINAS) {
      await page.goto(`http://127.0.0.1:${porta}${BASE}${rota}`, { waitUntil: "load" });
      await page.waitForTimeout(60);
      const m = await page.evaluate(MEDICAO);
      medidos++;
      if (m.pagina > w + 1) {
        problemas.push(`${nomePagina} @ ${rotulo}: a página rola para o lado (+${m.pagina - w}px)`);
      }
      for (const e of m.estouros.slice(0, 2)) {
        problemas.push(`${nomePagina} @ ${rotulo}: ${e.el} ultrapassa a viewport (dir=${e.dir}) «${e.texto}»`);
      }
      for (const c of m.cortados.slice(0, 2)) {
        problemas.push(`${nomePagina} @ ${rotulo}: ${c.el} cortado (${c.conteudo}px em caixa de ${c.caixa}px) «${c.texto}»`);
      }
      for (const a of m.alvos.slice(0, 4)) {
        const linha = `${a.w}x${a.h}px em ${a.el} «${a.rotulo}»`;
        if (a.grave) problemas.push(`alvo abaixo de 24px (WCAG 2.5.8 AA) em ${nomePagina} @ ${rotulo}: ${linha}`);
        else {
          const atual = avisos.get(linha) || { pagina: nomePagina, n: 0 };
          atual.n++;
          avisos.set(linha, atual);
        }
      }
    }
    await ctx.close();
  }

  await browser.close();
  server.close();

  console.log("=".repeat(72));
  console.log(`MEDIÇÃO DE RESPONSIVIDADE — ${medidos} medições (${PAGINAS.length} páginas × ${VIEWPORTS.length} telas)`);
  console.log("=".repeat(72));
  if (!problemas.length) {
    console.log("  ok    nenhuma rolagem lateral, corte ou alvo pequeno em nenhuma tela");
  } else {
    for (const p of problemas) console.log("  FALHA " + p);
  }
  if (avisos.size) {
    console.log("");
    console.log("  avisos (abaixo de 44px, ainda conformes — um por elemento, não por tela):");
    for (const [linha, info] of [...avisos].slice(0, 12)) {
      console.log(`        - ${linha}  [${info.n} ocorrência(s); ex.: ${info.pagina}]`);
    }
    if (avisos.size > 12) console.log(`        … e mais ${avisos.size - 12} elementos`);
  }
  console.log("-".repeat(72));
  console.log((problemas.length ? problemas.length + " problemas" : "tudo dentro do esperado") +
              (avisos.size ? ` · ${avisos.size} avisos` : ""));
  process.exit(problemas.length ? 1 : 0);
})().catch((e) => { console.error("ERRO NO HARNESS:", e.message); process.exit(2); });
