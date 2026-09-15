# Fluxos e estados

## Fluxo 1 — "Ele fez alguma coisa pela minha cidade?"

```
home → campo de busca (ou atalho "Ver os 26 registros")
     → /realizacoes/?municipio=marilia        ← o filtro já vem na URL
     → cartão → /realizacoes/{id}/
     → ficha: cargo, período, tipo de atuação, fontes com data de consulta
```

Pontos de decisão projetados:
- a home oferece **três** saídas explícitas, não onze;
- o filtro de município tem contagem por opção (`Marília (7)`), então o
  visitante sabe antes de clicar se existe conteúdo;
- o estado fica na URL, então a pessoa pode mandar o recorte para alguém.

## Fluxo 2 — "Isso é verdade? Onde está a prova?"

```
qualquer registro → carimbo de evidência (número + barra proporcional)
                  → seção "Documentos e fontes" (nome, tipo, nível, data de consulta)
                  → link externo da fonte
                  → /fontes/ (escala 50–100 e critério de cada nível)
```

O nível de evidência é **faceta** em `/realizacoes/`: dá para listar só o que
tem documento oficial (100) ou só o que tem base oficial (90+). A regra editorial
virou controle de interface.

## Fluxo 3 — "O que saiu de novo hoje?"

```
home (bloco Clipping) → /clipping/ → salto por dia → matéria no veículo original
                                    → filtro "só fontes oficiais"
```

## Fluxo 4 — teclado

| Tecla | Efeito |
| --- | --- |
| `/` ou `Ctrl`/`Cmd`+`K` | leva ao campo de busca de qualquer página |
| `↑` `↓` | percorre os resultados da busca |
| `Enter` | abre o resultado em foco |
| `Esc` | fecha menu/drawer, limpa a busca |
| `Tab` | preso dentro do drawer enquanto ele está aberto |

---

## Matriz de estados

Cada tela lista os estados que ela **tem que** tratar. Onde não há estado
declarado, ele foi tratado como inexistente de propósito.

### `/realizacoes/`

| Estado | Gatilho | O que aparece |
| --- | --- | --- |
| carregado | build | 12 de 26 cartões + "Mostrando 12 de 26" |
| filtrado | qualquer faceta | lista reduzida, etiquetas removíveis, URL atualizada |
| mais resultados | botão | +12 cartões por clique |
| fim da lista | último lote | botão "mostrar mais" some |
| vazio | combinação sem resultado | `.estado-vazio` explicando que ausência de registro ≠ ausência de atuação, com "Limpar filtros" |
| sem JavaScript | script bloqueado | os 26 cartões aparecem; barra de filtros fica inerte e o botão de densidade some (`html.sem-js`) |

### `/busca/`

| Estado | O que aparece |
| --- | --- |
| inicial | "Comece a digitar", tamanho do índice, sugestões clicáveis, buscas recentes (se houver) |
| digitando | debounce de 130 ms |
| resultados | contador, realce `<mark>` nos termos, filtro por tipo de conteúdo |
| vazio | "Nada encontrado para X" + explicar que o acervo só publica o que tem fonte + 3 saídas |
| sem JavaScript | `<noscript>` com índice curado de dossiês, temas e municípios |

### `/clipping/`

| Estado | O que aparece |
| --- | --- |
| com menções | agrupadas por dia (Hoje/Ontem/data), salto por dia, filtros |
| filtro sem resultado | dias vazios somem + `.estado-vazio` explicando que ausência de menção não é ausência de atuação |
| coleta vazia | texto explicando a rotina diária |

### Registro individual

| Estado | O que aparece |
| --- | --- |
| carregado | ficha, quatro seções narrativas, fontes, compartilhar, relacionadas |
| sem entidades | `—` explícito, nunca campo sumido |
| evidência baixa (60–69) | nota de evidência laranja visível no corpo |
| fim da leitura | anterior/próximo na mesma ordem da listagem |
| copiar link | confirmação no botão **e** anúncio em `aria-live`; se o clipboard falhar, mostra a URL |

### Global

| Estado | O que aparece |
| --- | --- |
| 404 | explicação do porquê + busca + atalhos com contagem |
| tema | claro / escuro / automático, persistido, aplicado antes da primeira pintura (sem *flash*) |
| movimento reduzido | transições e animações neutralizadas |
| alto contraste | bordas reforçadas, gradientes decorativos removidos |
| economia de dados | fundos decorativos desligados |
| impressão | chrome removido, cartões sem sombra, `break-inside: avoid` |
