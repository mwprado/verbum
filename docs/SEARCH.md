# Verbum — busca lexical por relevância

**Estado:** requisito para evolução futura, registrado em 17 de novembro de 2026.

Adotar a mesma semântica de busca aprovada no RetroVision, adaptada a verbetes e expressões lexicais.

## Requisitos

- Buscar substrings em qualquer posição do lema, não apenas no início.
- Termos separados por espaços representam OU inclusivo: retornar entradas que contenham um ou mais termos, priorizando a interseção.
- Ordenar por relevância: (1) lema completo igual à consulta; (2) consulta completa como substring contígua, na mesma ordem; (3) todos os termos encontrados, ainda que separados ou em ordem diferente; (4) correspondências parciais, pela quantidade decrescente de termos distintos encontrados.
- Não exigir aspas para reconhecer ou priorizar uma expressão exata. Um filtro explícito por expressão entre aspas permanece opcional.
- Preservar os filtros de idioma, dicionário e demais critérios ativos antes de calcular a relevância.
- Preservar homógrafos, acepções, fontes e grafias originais. Não fundir entradas lexicais distintas só porque a chave de busca coincide.
- Aplicar normalização Unicode e comparação sem distinção de caixa, de forma compatível com a coluna normalized existente no VLF. Tratamento de acentos: proposta de distinguir a grafia exata e oferecer correspondências sem acentos em prioridade inferior, sem alterar os dados originais; decisão final pendente.

## Exemplos ilustrativos

Consulta `água doce`: água doce (lema exato), peixe de água doce (expressão contígua), água de sabor doce (todos os termos separados), água potável e doce de leite (um termo).

Consulta `mar`: mar (lema exato), marinho, submarino e amar (substring).

Os exemplos demonstram a ordenação, não afirmam que todos os lemas estejam presentes em um dicionário específico.

## Implementação proposta

Separar a pesquisa de lemas da pesquisa de conteúdo das definições. A primeira usa a regra acima; a segunda pode continuar usando FTS5. Compartilhar a lógica de classificação entre GUI, CLI e futura API lexical, evitando divergências entre clientes.

O VLF v2 usa SQLite, índice de lemas normalizados e FTS5. Antes de alterar o formato, avaliar o custo de consultas por substring e o benefício de um índice trigram (incluindo compatibilidade com SQLite das distribuições suportadas e termos menores que três caracteres). Não tornar uma migração de formato obrigatória sem medir desempenho.

## Critérios de aceitação

Testar lema exato, expressão contígua, substring interna, termos em ordem inversa, união e interseção, consultas curtas, caixa, acentos, homógrafos, filtros e ausência de duplicações artificiais. Medir latência em catálogos grandes antes de escolher a estratégia de indexação.
