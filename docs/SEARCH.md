# Verbum — busca lexical por relevância

**Estado:** implementado em 17 de novembro de 2026.

A busca inteligente do Verbum usa relevância lexical sobre os lemas normalizados do VLF e mantém a correção ortográfica como fallback de prioridade inferior.

## Semântica

- Busca substrings em qualquer posição do lema, não apenas no início.
- Termos separados por espaços representam OU inclusivo: entram candidatos que contenham um ou mais termos.
- A interseção é priorizada automaticamente.
- Não é necessário usar aspas para que uma expressão completa receba prioridade.
- Os filtros de idioma, dicionário, origem e função são aplicados antes da classificação.
- Homógrafos e entradas distintas permanecem separados; a busca não funde registros pela chave normalizada.
- A comparação usa a coluna `normalized` do VLF, portanto é Unicode NFC e case-insensitive via `casefold()`.
- A correção ortográfica usa comparação sem diacríticos apenas para gerar sugestões, sempre abaixo das correspondências lexicais normais. Os dados e a grafia original nunca são alterados.

## Ordem de relevância

A busca `mode="smart"` classifica os resultados nesta ordem:

1. **exact** — o lema completo é igual à consulta;
2. **phrase** — a consulta completa ocorre como substring contígua no lema;
3. **all_terms** — todos os termos distintos aparecem no lema, mesmo separados ou em outra ordem;
4. **partial** — apenas parte dos termos aparece, priorizando a maior quantidade de termos distintos encontrados;
5. **similar** — sugestão por distância ortográfica, usada apenas para preencher vagas restantes.

Dentro da mesma classe, lemas menores e depois a ordem lexical normalizada são usados como critérios de desempate.

## Exemplos

Consulta `água doce`:

1. `água doce` — **exact**;
2. `peixe de água doce` — **phrase**;
3. `água de sabor doce` e `doce água mineral` — **all_terms**;
4. `água potável` e `doce de leite` — **partial**.

Consulta `mar`:

1. `mar` — **exact**;
2. `marinho`, `submarino` e `amar` — **phrase**, pois `mar` ocorre em qualquer posição do lema.

## Implementação

A pesquisa de lemas é independente da pesquisa de conteúdo das definições. A primeira usa a classificação descrita acima; a segunda continua disponível por FTS5 em `mode="fulltext"`.

Para cada dicionário selecionado, o SQLite calcula os componentes de relevância com `instr()` e devolve no máximo o `limit` local. Isso evita materializar todo o catálogo em Python. Como nenhum dicionário pode fornecer mais de `limit` itens para o top-N global, esse limite local não remove um resultado que poderia entrar na resposta final.

A ordenação final é compartilhada por `Registry.search()`, portanto GUI, CLI e futuros clientes da API lexical recebem a mesma semântica.

### Desempenho

Substring arbitrária (`%termo%`) não pode aproveitar diretamente o índice B-tree atual de `entries(normalized)`. A implementação evita uma migração obrigatória do VLF v2 e usa `instr()` sobre o catálogo selecionado.

Antes de introduzir índice trigram ou outra estrutura auxiliar, devem ser medidos catálogos grandes nas versões de SQLite suportadas pelo Fedora/EPEL. Termos menores que três caracteres também precisam permanecer funcionais sem depender de trigramas.

## Critérios cobertos por testes

A suíte cobre:

- lema exato;
- homógrafos exatos;
- substring interna;
- expressão contígua;
- termos separados;
- termos em ordem inversa;
- união e interseção;
- relevância por quantidade de termos;
- filtro por dicionário;
- ausência de fusão artificial de entradas.

Ainda é recomendável medir latência com os maiores VLF reais antes de alterar o formato de armazenamento.
