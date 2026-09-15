# Walter Ihoshi — Acervo de Atuação Pública

Site público, independente e altamente indexável que funciona como **base estruturada de evidências** da trajetória, realizações, projetos, ações e atuação pública de **Walter Shindi Iihoshi** (uso público frequente: *Walter Ihoshi*).

> **Veja o que foi feito. Consulte as fontes.**

Princípio central: `FATO → EVIDÊNCIA → CONTEXTO → TERRITÓRIO → TEMA → FONTE`. Nenhuma realização é publicada sem fonte verificável; participação não vira autoria; apoio não vira realização individual; promessa não vira entrega.

## Estrutura

| Rota | Conteúdo |
| --- | --- |
| `/` | Home com busca, destaques, temas, localidades e atualizações |
| `/realizacoes/` | Base completa de registros (+ página individual por registro) |
| `/temas/` | Organização temática (ex.: `/temas/cadastro-positivo/`) |
| `/municipios/` | Páginas territoriais apenas com evidência real (ex.: `/municipios/marilia/`) |
| `/linha-do-tempo/` | Trajetória cronológica documentada (1961–2026) |
| `/mandatos/` | Atuação parlamentar na Câmara dos Deputados |
| `/jucesp/` | Dossiê da presidência da Jucesp (2019–2023) |
| `/convenios/` | Diretoria de convênios do Governo de SP (2023–2026) |
| `/comunidade-nikkei/` | Relação histórica com a comunidade nipo-brasileira |
| `/fontes/` | Metodologia, fontes catalogadas e níveis de evidência |
| `/atualizacoes/` | Novos registros incorporados ao acervo |
| `/clipping/` | Clipping do dia: menções a Walter Ihoshi na imprensa (coleta automática) |
| `/busca/` | Busca global (funciona offline, no próprio HTML) |

Cada registro identifica: **tipo de atuação** (autoria, relatoria, gestão, articulação, emenda, evento…), cargo exercido, período, resultado documentado, fontes com URL e data de consulta, e **nível de evidência** (escala 50–100; abaixo de 60 não é publicado como fato).

## Dados estruturados

Todo o conteúdo vive em `data/`, auditável e editável:

```
data/
  config.json          # identidade, URLs, dados da candidatura 2026
  pessoa.json          # biografia oficial, cargos, grafias do nome
  realizacoes.json     # base de registros (o coração do acervo)
  temas.json           # organização temática
  municipios.json      # páginas territoriais
  timeline.json        # linha do tempo
  eleicoes.json        # histórico eleitoral
  fontes.json          # catálogo de fontes com nível de evidência
  atualizacoes.json    # log de incorporações
  monitoramento/       # fila de validação e itens já vistos
  bruto/               # coletas da API da Câmara (não publicado)
```

## Como rodar

```bash
python3 scripts/coletar_camara.py   # opcional: coleta dados da API da Câmara
python3 scripts/monitorar.py        # opcional: monitora novas menções -> fila
python3 scripts/gerar.py            # gera o site em public/
```

Dependências: **apenas Python 3 padrão** (sem frameworks). O site é 100% estático, renderizado no build — conteúdo crítico não depende de JavaScript.

### Verificação de UX e acessibilidade

```bash
python3 scripts/gerar.py
python3 scripts/testar_ux.py            # 17 checagens sobre o HTML gerado (sem dependências)
node scripts/testar_ux_interacoes.js    # opcional: exercita o app.js real no jsdom (npm i --no-save jsdom)
node scripts/medir_responsividade.js    # opcional: mede o layout real em 14 páginas × 9 telas (npm i playwright)
```

As suítes rodam sobre o que **sai do build**, não sobre uma reimplementação, e saem com código 1 em qualquer falha. A medição de responsividade abre um Chromium de verdade e reprova rolagem lateral da página, conteúdo cortado e alvo de toque abaixo de 24×24 (WCAG 2.5.8).

## UX e acessibilidade

As decisões de projeto estão documentadas em [`docs/ux/`](docs/ux/): arquitetura de informação, fluxos e matriz de estados, regras de acessibilidade e como verificar.

Resumo do que a interface faz:

- **Navegação agrupada por intenção** (Acervo / Dossiês / Acompanhe) com `aria-current`, drawer mobile com foco preso e `Esc`, e trilha de navegação como landmark em toda página interna.
- **Facetas em `/realizacoes/`**: texto, tipo de atuação, tema, município e nível mínimo de evidência, com ordenação, contagem anunciada, revelação progressiva, densidade alternável e **estado dos filtros na URL** (recorte compartilhável).
- **Busca instantânea** com realce dos termos, filtro por tipo de conteúdo, navegação por teclado (`/` ou `Ctrl`+`K`, `↑`/`↓`, `Enter`, `Esc`), buscas recentes e alternativa navegável sem JavaScript.
- **Estados sempre declarados**: vazio, erro, 404 e fim de lista têm explicação e ação de saída — nenhuma tela morta.
- **Sumário gerado no build** com scroll-spy nas páginas longas, barra de progresso de leitura e voltar ao topo.
- **Tema claro/escuro/automático** persistido e aplicado antes da primeira pintura.
- **Progressive enhancement**: o `app.js` só acelera; com script bloqueado o acervo continua completo.
- **Responsivo de fato**: sem rolagem lateral da página em nenhuma das 9 larguras medidas (280–1440px) e em nenhuma das 61 páginas. Grades, tabelas, facetas e o topo foram corrigidos a partir de medição em navegador — ver [`docs/ux/responsividade-e-medicao.md`](docs/ux/responsividade-e-medicao.md).
- **Celular com a ação na primeira tela**: no hero, busca e atalhos vêm antes do texto de apoio; tabela larga rola dentro do próprio bloco, com dica e rótulo acessível.

### Deploy

- **GitHub Pages**: publique a pasta `public/` (ou use o workflow incluído). Ajuste `site_url`/`base_path` em `data/config.json`.
- **Vercel/Netlify**: build command `python3 scripts/gerar.py`, output directory `public`.

### Automação (GitHub Actions)

`.github/workflows/atualizar.yml` executa diariamente: coleta na Câmara → monitoramento de menções → regeneração do site → commit. O pipeline segue `COLETA → DEDUPLICAÇÃO → CLASSIFICAÇÃO → VALIDAÇÃO → PUBLICAÇÃO`, e **nada é publicado automaticamente**: novos itens entram em `data/monitoramento/fila.json` com status *aguardando validação*.

## Como adicionar um registro

1. Adicione o objeto em `data/realizacoes.json` (campos obrigatórios: título, resumo factual, data/período, cargo, tipo de atuação, temas, municípios, fontes, `evidence_score`).
2. Cadastre toda fonte nova em `data/fontes.json` (nome, tipo, nível, URL, data de consulta).
3. Se aplicável, referencie o registro em temas, municípios e linha do tempo.
4. Registre a incorporação em `data/atualizacoes.json` e rode `python3 scripts/gerar.py`.

## Regras de conteúdo (resumo)

**Proibido**: inventar números/resultados; atribuir autoria sem prova; converter participação em autoria ou promessa em entrega; páginas territoriais vazias; conteúdo SEO artificial sem evidência; confundir candidato com ocupante de mandato.

**Obrigatório**: fatos, datas, documentos, fontes com link, linguagem clara, distinção entre proposta e realização.

## Identificação do responsável (período eleitoral)

Walter Ihoshi é candidato a deputado federal por São Paulo (PSD, nº 5599) nas eleições de 2026. O responsável pela publicação deste site, exibido no rodapé de todas as páginas, está definido em `data/config.json`:

- **Responsável:** Leandro Calado — [lcfconsulting.com.br](https://lcfconsulting.com.br)

O acervo não realiza impulsionamento nem publicidade paga; registros baseados apenas em fontes de período eleitoral carregam nota de evidência visível.

## Clipping diário (o que sai de novo, todos os dias)

A rotina `scripts/monitorar.py` roda **duas vezes por dia** via GitHub Actions (08:17 e 20:17, horário de Brasília) e garante as novidades do dia:

1. **Coleta** — varre o Google News RSS com três consultas (`"Walter Ihoshi"`, `"Walter Iihoshi"`, `"Walter Shindi"`), cobrindo imprensa nacional e regional;
2. **Deduplicação** — itens já vistos ficam registrados em `data/monitoramento/vistos.json`;
3. **Classificação** — tema e município propostos por palavras-chave;
4. **Publicação no clipping** — menções inéditas entram em `data/monitoramento/clipping.json` e aparecem automaticamente na página `/clipping/` (agrupadas por dia: Hoje, Ontem, …), na home e no feed RSS;
5. **Fila de validação** — menções provenientes de fontes oficiais/institucionais entram também em `data/monitoramento/fila.json` como candidatas a **registro verificado** do acervo (nada vira registro sem curadoria).

### Publicação automática do site

O mesmo workflow publica o site regenerado na branch **`gh-pages`** a cada execução. Para ativar o endereço público `https://<usuario>.github.io/walterihoshi/`, habilite o GitHub Pages do repositório apontando para a branch `gh-pages` (Settings → Pages). Ajuste `site_url`/`base_path` em `data/config.json` se usar domínio próprio.

> Nota: workflows agendados (`schedule`) só executam a partir da branch padrão — após o merge deste PR para `main`, o cron passa a valer automaticamente.

## Nota sobre o nome

O nome civil é **Walter Shindi Iihoshi** (grafia da Câmara e do TSE); o uso público frequente é **Walter Ihoshi**. O site trabalha as duas grafias como variantes de busca equivalentes (ver `data/pessoa.json`) sem criar informação inconsistente.

---

Projeto de documentação pública. Histórico de alterações auditável pelo Git.
