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

## ⚠️ Pendência obrigatória antes da publicação em período eleitoral

Walter Ihoshi é candidato a deputado federal por São Paulo (PSD, nº 5599) nas eleições de 2026. Antes de publicar o site em período eleitoral, complete em `data/config.json`:

- `autor.responsavel` — nome do responsável pela publicação (exigência de identificação em material eleitoral);
- `autor.contato` — canal para correções.

O rodapé do site exibirá essa identificação automaticamente. O acervo não realiza impulsionamento nem publicidade paga; registros baseados apenas em fontes de período eleitoral carregam nota de evidência visível.

## Nota sobre o nome

O nome civil é **Walter Shindi Iihoshi** (grafia da Câmara e do TSE); o uso público frequente é **Walter Ihoshi**. O site trabalha as duas grafias como variantes de busca equivalentes (ver `data/pessoa.json`) sem criar informação inconsistente.

---

Projeto de documentação pública. Histórico de alterações auditável pelo Git.
