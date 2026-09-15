# Responsividade — o que foi medido e o que mudou

Este documento existe porque a responsividade deste site **já foi verificada por
construção** (breakpoints, `clamp()`, `min-height`, tokens) e mesmo assim tinha
defeitos que só aparecem quando um navegador de verdade calcula o layout. As
medições abaixo foram feitas em Chromium headless, sobre o HTML/CSS que sai do
build, em 14 páginas × 9 larguras de tela (280 a 1440px).

Nada aqui é opinião de estilo: cada item é uma medida antes/depois.

## O que estava quebrado (medido)

**1. A página inteira rolava para o lado.**

| Página | Tela | Rolagem lateral |
| --- | --- | --- |
| `/clipping/` | 360px | **+130px** (conteúdo de 490px) |
| `/clipping/` | 768px | +76px |
| `/mandatos/` | 320px | +62px |
| `/fontes/` | 320px | +39px |
| home, `/realizacoes/`, `/temas/`, `/municipios/`, `/busca/`, `/jucesp/`, `/comunidade-nikkei/` | 320px | +16px |

Três causas distintas:

- **`.chip-opcao span` com `white-space: nowrap`.** O rótulo
  *"Somente fontes oficiais/institucionais (80+)"* media 453px e não podia
  quebrar — arrastava a página junto no `/clipping/`.
- **Grade com `minmax(320px, 1fr)`.** Em telas de 320px a faixa ficava *mais
  larga que o container* (320px dentro de 288px úteis). Não é o navegador
  esticando: é a grade pedindo 320px onde só cabem 288px.
- **Tabela sem contêiner rolável.** Em `/mandatos/` e `/fontes/` a tabela
  (366px, 343px) era o elemento mais largo da página, e o `<table>` empurrava o
  documento inteiro.

**2. Um falso positivo que valeu a pena investigar.** Em *toda* largura de
desktop, os cartões de tema e município apareciam com `scrollWidth` de 393px
dentro de uma caixa de 363px — ou seja, 30px "escondidos" por `overflow: hidden`.
Fui atrás: os 30px eram o brilho decorativo (`.card-tema::after`, um radial em
`right: -30px`), não texto. **Nenhum conteúdo legível estava cortado.** A causa
real do aperto era a faixa da grade, corrigida no item 1, e o `::after` continua
sendo recortado pela borda do cartão de propósito.

A lição ficou no harness: um `scrollWidth` maior que a caixa não é defeito por si
só — só conta quando algum **filho real** ultrapassa a caixa. Sem esse filtro, a
medição acusaria decoração para sempre e ninguém olharia mais o relatório.

**3. A busca do hero virava um risco.** Com `display: flex` fixo, em 320px o
campo de texto ficava com **38px de largura** ao lado de um botão de 206px.

**4. Tabela espremida em tira vertical.** Sem largura mínima, as colunas de
`/mandatos/` quebravam em 2–3 linhas por célula a 360px — legível, mas péssimo.

**5. Alvos de toque abaixo do que o projeto declara.** O token `--alvo: 44px`
existia, mas não era usado em: `.util` e `.nav-item` (40px), links do menu
suspenso (43px), `.ver-tudo` (35px), trilha (22px), links do rodapé (23px),
`.drawer-fechar` (40px), ações dos filtros (38px). A checagem antiga só conferia
a *presença do token*, não o uso.

**6. Ordem errada no celular.** No hero, abaixo de 560px a primeira tela
mostrava título, subtítulo e três parágrafos — a busca e os atalhos só apareciam
depois de rolar. Nenhuma ação visível na dobra.

## O que mudou

| Defeito | Correção |
| --- | --- |
| Rolagem lateral da página | grades com `minmax(min(320px, 100%), 1fr)`; `.chip-opcao span` quebra em vez de não quebrar; **toda** tabela passa a ser gerada por `tabela_responsiva()` |
| Falso positivo na medição | o detector de corte passou a exigir que um **filho real** ultrapasse a caixa, para não acusar `::after` decorativo |
| Tabela | `.tabela-wrap` (`overflow-x: auto`, focoável, `role="region"` + `aria-label`), sombra nas bordas como pista visual (CSS puro) e `.tabela-wrap > .tabela { min-width: 480px }` em telas pequenas + dica textual visível |
| Busca do hero | abaixo de 560px empilha em coluna, campo e botão com largura total |
| Hero no celular | reordenado por `flex order` (título → subtítulo → busca → atalhos → texto de apoio). Só há um elemento focável, então a ordem de tabulação não muda |
| Topo em 320px | `–topo-altura` sobe para 74px, marca quebra em duas linhas, espaçamentos apertados |
| Alvos de toque | `.util`, `.nav-item`, `.nav-menu a`, `.drawer-fechar`, `.ver-tudo`, `.compartilhar`, `.filtro-acoes .btn` usam `var(--alvo)`; trilha 32px, sumário 34px, rodapé 34px |

## Resultado da medição (depois)

```
MEDIÇÃO DE RESPONSIVIDADE — 126 medições (14 páginas × 9 telas)
  ok    nenhuma rolagem lateral, corte ou alvo pequeno em nenhuma tela
  avisos (abaixo de 44px, ainda conformes — um por elemento, não por tela): 44
```

Zero falhas. Os 44 avisos são elementos entre 24px e 44px (por exemplo o botão
de tema com 43×44px e os chips de 32px de altura) — abaixo do alvo confortável
que o projeto persegue, acima do piso `AA` da WCAG 2.5.8. Ficam registrados, não
escondidos.

## Regras que passam a valer

1. **A rolagem horizontal pertence ao bloco, nunca à página.** Tabela larga rola
   dentro de `.tabela-wrap`; nenhum outro elemento pode ultrapassar a viewport.
2. **Grade sempre com `minmax(min(LARGURA, 100%), 1fr)`.** Um valor fixo dentro
   de `minmax()` é maior que a tela em algum celular.
3. **Rótulo de faceta não usa `nowrap`.** Texto de interface quebra; se não
   couber, o problema é o texto, não a tela.
4. **Alvo de toque: 44px onde é ação principal** (`var(--alvo)`) e nunca menos de
   24px em controle nenhum (WCAG 2.5.8).
5. **A primeira tela do celular mostra o que fazer.** Conteúdo de apoio vem
   depois das ações.
6. **Toda tabela nasce do helper `tabela_responsiva()`**, que já entrega
   contêiner rolável, rótulo acessível e dica. Tabela escrita à mão fora dele
   falha na verificação.

## Como verificar

```bash
python3 scripts/gerar.py
python3 scripts/testar_ux.py                     # 17 checagens, sem dependências

npm install playwright && npx playwright install chromium   # só na primeira vez
node scripts/medir_responsividade.js             # medição em navegador real
```

- `scripts/testar_ux.py` (checagens 16 e 17) garante o **padrão**: grade com
  `min()`, toda tabela dentro de `.tabela-wrap` rotulado, `.chip-opcao` sem
  `nowrap`, empilhamento da busca e alvos de 44px nas ações. Roda sem
  dependências e falha o build.
- `scripts/medir_responsividade.js` mede o **resultado**: rolagem lateral, corte
  e tamanho real de alvo em 126 combinações de página × tela. Exige Playwright
  (ferramenta de desenvolvimento; o site publicado continua sem dependência
  nenhuma). Em contêiner onde o Chromium já existe, use
  `CHROMIUM_PATH=/usr/bin/chromium node scripts/medir_responsividade.js`.

Um valor de `--topo-altura` diferente do real quebra âncoras e sumário: em telas
de 340px ou menos ele sobe para 74px junto com o topo de duas linhas. Por isso os
dois são definidos no mesmo bloco `@media`.
