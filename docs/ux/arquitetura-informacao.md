# Arquitetura de informação

## O problema de organização

O acervo tem três naturezas de conteúdo misturadas, e a navegação antiga tratava
as três do mesmo jeito: uma linha com 10 links do mesmo peso.

- **Base** — 26 registros atômicos, cada um com fonte.
- **Recortes** — os mesmos registros vistos por tema (15) e por município (6).
- **Narrativas** — dossiês longos (mandatos, Jucesp, convênios, comunidade nikkei)
  e a linha do tempo (24 marcos).

Mais: **rastreamento** (clipping diário, atualizações) e **transparência**
(fontes e método).

## O agrupamento adotado

Três grupos por intenção de visita, definidos em `GRUPOS_NAV` (`scripts/gerar.py`):

```
Acervo      → "o que foi feito"        Realizações · Temas · Municípios · Linha do tempo
Dossiês     → "aprofunde um capítulo"  Mandatos · Jucesp · Convênios · Comunidade nikkei
Acompanhe   → "o que está saindo"      Clipping do dia · Atualizações · Fontes e método
```

**Decisão de apresentação:** no desktop, `Acervo` fica sempre visível (é o
caminho principal) e os outros dois viram `<details>` reveláveis. No drawer
mobile, os três aparecem como seções rotuladas — agrupar não é esconder.

Escolheu-se `<details>/<summary>` em vez de menu JavaScript porque o
comportamento de abrir/fechar por teclado é nativo e funciona sem script.

## Rotas

| Rota | Papel na IA |
| --- | --- |
| `/` | Ponto de decisão: buscar, ver a base, ver o que saiu hoje, entender o método |
| `/realizacoes/` | **A base.** Lista facetada — é a página de trabalho do site |
| `/realizacoes/{id}/` | Unidade atômica de evidência |
| `/temas/`, `/temas/{id}/` | Recorte temático |
| `/municipios/`, `/municipios/{id}/` | Recorte territorial |
| `/linha-do-tempo/` | Ordenação cronológica |
| `/mandatos/`, `/jucesp/`, `/convenios/`, `/comunidade-nikkei/` | Dossiês |
| `/clipping/` | Rastreamento diário (menção ≠ registro) |
| `/atualizacoes/` | Log de incorporações |
| `/fontes/` | Metodologia e catálogo de fontes |
| `/busca/` | Corte transversal a tudo |

## Hierarquia de títulos

Regra verificada automaticamente: **o chrome da página não emite `<h2>`**.
Títulos de coluna do rodapé e do drawer são `<p class="rodape-titulo">` /
`<p class="drawer-grupo-titulo">`. Assim, quem navega por títulos num leitor de
tela encontra só o conteúdo real, na ordem `h1 → h2 → h3`, sem saltos de nível.

## Busca: o que entra no índice

`montar_indice_busca()` indexa 87 itens nesta versão: registros (com cargo,
período, entidades, temas e municípios como campo de busca), temas, municípios,
dossiês, marcos da linha do tempo e as 40 menções mais recentes do clipping.

O índice vai embutido na página (`<script type="application/json">`) e também é
publicado em `/search-index.json`. A busca funciona offline, sem rede depois do
primeiro carregamento.

## Separar menção de registro é decisão de IA

`/clipping/` nunca é apresentado como realização. O topo da página traz o aviso
"como ler esta página", a faceta separa fontes oficiais de imprensa, e o único
caminho de uma menção para a base é a curadoria — descrita em `/fontes/`.
