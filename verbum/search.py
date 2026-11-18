"""Ranked lexical search, with a bounded cached spelling index."""
from collections import defaultdict
from functools import lru_cache
from contextlib import closing
import unicodedata


def fold(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )


def grams(text):
    return {text[i:i + 2] for i in range(len(text) - 1)}


def distance(a, b):
    """Optimal string alignment distance, including adjacent transposition."""
    prevprev = None
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        row = [i]
        for j, y in enumerate(b, 1):
            value = min(
                row[j - 1] + 1,
                prev[j] + 1,
                prev[j - 1] + (x != y),
            )
            if (
                i > 1
                and j > 1
                and x == b[j - 2]
                and a[i - 2] == y
            ):
                value = min(value, prevprev[j - 2] + 1)
            row.append(value)
        prevprev, prev = prev, row
    return prev[-1]


@lru_cache(maxsize=4)
def spelling_index(path, signature):
    from .core import connect_read

    words = defaultdict(list)
    buckets = defaultdict(set)
    with closing(connect_read(path)) as db:
        for (word,) in db.execute("SELECT DISTINCT normalized FROM entries"):
            key = fold(word)
            words[key].append(word)
            for gram in grams(key):
                buckets[gram].add(key)
    return words, buckets


def similar(path, key, limit=20):
    if len(key) < 3 or len(key) > 80:
        return []

    stat = path.stat()
    words, buckets = spelling_index(
        str(path),
        (stat.st_ino, stat.st_size, stat.st_mtime_ns),
    )
    query = fold(key)
    threshold = 1 if len(query) <= 4 else 2
    candidates = defaultdict(int)

    for gram in grams(query):
        for word in buckets.get(gram, ()):
            if abs(len(word) - len(query)) <= threshold:
                candidates[word] += 1

    # Short words may share no bigram after a single typo.
    if len(query) <= 4:
        for word in words:
            if abs(len(word) - len(query)) <= threshold:
                candidates.setdefault(word, 0)

    ranked = []
    for word, _ in sorted(
        candidates.items(),
        key=lambda item: (-item[1], abs(len(item[0]) - len(query)), item[0]),
    )[:4000]:
        edit_distance = distance(query, word)
        if edit_distance <= threshold:
            for original in words[word]:
                if original != key and not original.startswith(key):
                    ranked.append((edit_distance, original))

    return sorted(ranked)[:limit]


def _query_terms(key):
    """Return distinct normalized terms while preserving query order."""
    return list(dict.fromkeys(part for part in key.split() if part))


def _lexical_rows(db, key, terms, limit):
    """Return the best lexical candidates from one dictionary.

    SQLite computes the relevance dimensions so substring searches do not
    require materializing the entire dictionary in Python.
    """
    term_score = " + ".join("CASE WHEN instr(normalized, ?) > 0 THEN 1 ELSE 0 END" for _ in terms)
    where = " OR ".join("instr(normalized, ?) > 0" for _ in terms)

    sql = f"""
        SELECT id, payload, normalized,
               CASE WHEN normalized = ? THEN 1 ELSE 0 END AS exact_score,
               CASE WHEN instr(normalized, ?) > 0 THEN 1 ELSE 0 END AS phrase_score,
               ({term_score}) AS term_score
          FROM entries
         WHERE {where}
         ORDER BY exact_score DESC,
                  phrase_score DESC,
                  term_score DESC,
                  length(normalized),
                  normalized,
                  id
         LIMIT ?
    """

    params = [key, key, *terms, *terms, limit]
    return db.execute(sql, params).fetchall()


def _rank_key(item):
    score, hit = item
    lemma = hit["entry"].get("lemma", "")
    from .core import normalize

    return (
        score[0],
        score[1],
        len(normalize(lemma)),
        normalize(lemma),
        hit["dictionary"],
        hit["entry_id"],
    )


def ranked_search(registry, query, selected, paths, limit):
    """Search lemmas using lexical relevance before spelling similarity.

    Relevance order:
      1. complete lemma equals the query;
      2. complete query occurs as a contiguous substring;
      3. all distinct query terms occur in the lemma;
      4. partial matches, by descending number of distinct matched terms;
      5. spelling suggestions.
    """
    import json
    from pathlib import Path

    from .core import connect_read, normalize

    key = normalize(query)
    terms = _query_terms(key)
    result = []
    seen = set()

    def add(manifest, entry_id, payload, match, score):
        ident = (manifest["slug"], entry_id)
        if ident in seen:
            return
        seen.add(ident)
        result.append(
            (
                score,
                {
                    "dictionary": manifest["slug"],
                    "entry_id": entry_id,
                    "entry": json.loads(payload),
                    "match": match,
                },
            )
        )

    # Query at most `limit` candidates per dictionary. No dictionary can
    # contribute more than `limit` entries to the final global top-N, so this
    # bound does not discard a possible result.
    for manifest in selected:
        with closing(connect_read(paths[manifest["id"]])) as db:
            for entry_id, payload, normalized, exact, phrase, term_count in _lexical_rows(
                db,
                key,
                terms,
                limit,
            ):
                if exact:
                    match = "exact"
                    tier = 0
                elif phrase:
                    match = "phrase"
                    tier = 1
                elif term_count == len(terms):
                    match = "all_terms"
                    tier = 2
                else:
                    match = "partial"
                    tier = 3

                # Lower tuples sort first. Partial results therefore prefer
                # more distinct query terms.
                add(
                    manifest,
                    entry_id,
                    payload,
                    match,
                    (tier, -term_count),
                )

    result.sort(key=_rank_key)
    if len(result) >= limit:
        return [hit for _, hit in result[:limit]]

    # Keep typo correction strictly below lexical relevance. It fills unused
    # result slots but never displaces exact/substring/term matches.
    remaining = limit - len(result)
    for manifest in selected:
        if remaining <= 0:
            break
        path = Path(paths[manifest["id"]])
        with closing(connect_read(path)) as db:
            for edit_distance, word in similar(path, key, limit=remaining):
                rows = db.execute(
                    "SELECT id,payload FROM entries "
                    "WHERE normalized=? ORDER BY id LIMIT ?",
                    (word, remaining),
                )
                for entry_id, payload in rows:
                    add(
                        manifest,
                        entry_id,
                        payload,
                        "similar",
                        (4 + edit_distance, 0),
                    )
                    remaining = limit - len(result)
                    if remaining <= 0:
                        break
                if remaining <= 0:
                    break

    result.sort(key=_rank_key)
    return [hit for _, hit in result[:limit]]
