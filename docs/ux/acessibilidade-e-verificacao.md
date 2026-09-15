# Acessibilidade e verificação

## Regras que o código segue

**Contraste.** Nenhum token de texto informativo fica abaixo de 4,5:1
(WCAG 2.1 AA). Isso foi corrigido de fato: o `--tinta-3` antigo (`#8b94a8`)
media **2,87:1** sobre o fundo claro e **4,27:1** no escuro — abaixo do mínimo —
e era usado em `.fonte-meta`, `.tl-fontes`, `.clip-meta` e na trilha. Hoje é
`#64708a` no claro e `#93a0b8` no escuro. A checagem recalcula os pares a cada
build, então um token novo não passa sem medir.

**Foco visível em tudo.** `:focus-visible` com contorno de 3 px e `outline-offset`,
inclusive dentro do topo escuro (cor de foco diferente lá). Cartão com link
esticado recebe `:focus-within` com o mesmo contorno — o clique é no cartão
inteiro, mas a parada de tabulação continua sendo uma só, no título.

**Área de toque.** Controles primários têm `min-height: 44px` (token `--alvo`);
chips secundários nunca ficam abaixo de 24×24.

**Nomes acessíveis.** Nenhum campo depende só de `placeholder`. Cada `<input>` e
`<select>` tem `<label for>`; os `<input>` das facetas ficam *dentro* do
`<label>`, o que funciona sem JavaScript por construção.

**Landmarks e ordem.** Um `<h1>` por página; `<main>` focável com `tabindex="-1"`
para receber o salto do "pular para o conteúdo"; trilha como
`<nav aria-label="Trilha de navegação"><ol>`; sumário como `<nav aria-label="Índice
desta página">`; rodapé e drawer sem `<h2>` para não poluir a hierarquia.

**Preferências do usuário.** `prefers-reduced-motion`, `prefers-contrast: more`,
`prefers-reduced-data` e `print` têm blocos próprios. O tema manual
(`data-tema`) convive com `prefers-color-scheme` sem brigar: o automático é o
padrão e a escolha explícita vence.

**Anúncios.** Existe uma única região `#avisos` (`role="status"`,
`aria-live="polite"`) que recebe: mudança de tema, contagem de resultados da
busca, filtros limpos e confirmação de cópia de link.

## Verificação

Duas suítes, as duas rodando sobre o que **sai do build** — não sobre uma
reimplementação.

### 1. Estrutura e conteúdo (Python, sem dependências)

```bash
python3 scripts/gerar.py
python3 scripts/testar_ux.py
```

15 checagens sobre as 61 páginas HTML geradas:

1. estrutura de página (skip link primeiro no `<body>`, `<main>` focável, container, live region, tema, menu, `app.js` carregado)
2. conteúdo principal dentro do container
3. navegação (menu com `aria-expanded`/`aria-controls`, drawer como `dialog` modal, `<h1>` único)
4. trilha como landmark em toda página interna
5. campos com nome acessível
6. facetas de `/realizacoes/` (filtros, contagem anunciada, estado vazio, atributos de filtragem em todos os cartões)
7. busca (campo, índice JSON válido, contador, limpar, `<noscript>`)
8. integridade de links internos e âncoras
9. estados vazios e de erro definidos e usados
10. contraste dos tokens de texto (claro e escuro)
11. alvos de toque, foco visível e blocos de preferência
12. módulos e comportamentos presentes no `app.js`
13. página 404 com caminho de recuperação e fora do sitemap
14. orientação em páginas longas (sumário, salto por seção ou atalhos)
15. hierarquia de títulos sem saltos e com o chrome sem `<h2>`

Sai com código 1 em qualquer falha — dá para plugar no CI.

### 2. Interação (Node + jsdom, opcional)

```bash
npm install --no-save jsdom
node scripts/testar_ux_interacoes.js
```

Carrega o `app.js` real dentro do HTML real gerado e exercita: revelação
progressiva, filtro por texto, combinação de facetas, estado vazio, limpar
filtros, ordenação A–Z e por evidência, "mostrar mais" até o fim, densidade
persistida, busca com acento e realce, filtro por categoria, copiar link e seu
anúncio, alternância e persistência de tema, abrir/fechar o drawer com `Esc`,
`<details>` fechando ao clicar fora, filtro por década e filtros do clipping.

O `node_modules/` está no `.gitignore`. O site publicado continua sem nenhuma
dependência — isto é ferramenta de desenvolvimento.

### Nota sobre o que não foi verificado

Não há navegador no ambiente onde isto foi escrito, então **renderização visual
e responsividade real não foram inspecionadas** — foram verificadas por
construção (breakpoints, `clamp()`, `min-height`, tokens) e pelas checagens
estruturais acima. Métricas de Core Web Vitals também não foram medidas.
