# UX do Acervo — decisões de projeto

Este diretório registra **por que** a interface é como é. Não é descrição do que
já está no código; é o raciocínio que o código implementa, para que a próxima
alteração não desfaça uma decisão sem saber que ela foi tomada.

| Documento | Conteúdo |
| --- | --- |
| [arquitetura-informacao.md](arquitetura-informacao.md) | Como o conteúdo está organizado e por quê |
| [fluxos-e-estados.md](fluxos-e-estados.md) | Fluxos principais e a matriz de estados de cada tela |
| [acessibilidade-e-verificacao.md](acessibilidade-e-verificacao.md) | Regras de acessibilidade e como verificar |

---

## Princípios que governam a interface

**1. O conteúdo existe sem JavaScript.**
Toda página é renderizada no build. O `app.js` é *aprimoramento*: filtra,
ordena, revela mais, persiste preferências. Se ele falhar — rede lenta,
bloqueio de script, navegador antigo — o visitante continua lendo tudo.
Por isso cada módulo do `app.js` roda isolado em `try/catch` e nenhuma
informação existe apenas no cliente.

**2. Toda lista declara o que acontece quando está vazia.**
Não existe `<p>Nenhum registro.</p>` solto. Existe um componente de estado
(`.estado`, `.estado-vazio`, `.estado-erro`) com título, explicação e uma ação
de saída. Um filtro que não retorna nada diz *por que* e oferece o botão para
desfazer.

**3. Nunca deixar o visitante num beco sem saída.**
Fim de registro tem anterior/próximo. Erro 404 tem busca e atalhos. Estado
vazio tem ação. Rodapé repete a navegação inteira.

**4. O estado da visita pertence ao visitante.**
Filtros vão para a URL (`?tipo=LEI&tema=credito`), então um recorte pode ser
compartilhado ou recarregado. Tema e densidade ficam em `localStorage`. Voltar
no navegador não perde o que estava sendo feito.

**5. Evidência é interface, não rodapé.**
O nível de evidência aparece como carimbo com barra proporcional no cartão, na
ficha e no clipping, e é *faceta de filtro*. A regra editorial do projeto
("nada sem fonte") precisa ser visível na navegação, não só na metodologia.

**6. Uma decisão primária por tela.**
A home tem três atalhos explícitos. A página de base tem a barra de filtros.
A busca tem o campo. Nada compete com o objetivo da página.

---

## Padrões de componente

| Componente | Onde | Comportamento |
| --- | --- | --- |
| `.card` com link esticado | listas de registros | o cartão inteiro é clicável, mas o foco do teclado fica só no título — sem duplicar parada de tabulação |
| `.estado` | qualquer lista | título + explicação + ações; variante `.estado-erro` |
| `.filtros` | `/realizacoes/`, `/clipping/` | campos rotulados, chips de faceta com contagem, etiquetas removíveis do que está aplicado, contagem em `aria-live` |
| `.sumario` | páginas com 6 mil+ caracteres e 4+ seções | gerado no build a partir dos `<h2>`, com scroll-spy |
| `.trilha` | toda página interna | `<nav aria-label>` + `<ol>`, nunca texto solto com barras |
| `.chip-opcao` | facetas | `<input>` real dentro do `<label>` — funciona sem JS e é acessível por construção |
| `.badge.ev-*` | registros e clipping | cor + barra proporcional + `title` com o número |

## O que deliberadamente **não** foi feito

- **Carrossel** na home: esconde conteúdo e quebra leitura por teclado.
- **Menu hambúrguer no desktop**: com 10 destinos, agrupar e mostrar é mais
  rápido do que esconder atrás de um clique.
- **Infinite scroll**: quebra o "voltar" do navegador e a noção de fim de lista.
  Usa revelação progressiva com botão.
- **Animação de entrada nos cartões**: decora sem informar, e custa caro em
  aparelhos modestos — que é justamente o público de uma página pública.
