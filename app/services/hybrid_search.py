from ..models.db import get_messages_by_ids, search_messages_fts
from .embedding_service import semantic_search


def search(query, limit=20, mode="hybrid"):
    if not query:
        return []

    if mode == "semantic":
        return _pure_vector(query, limit)

    if mode == "keyword":
        return _pure_fts(query, limit)

    fts_results = search_messages_fts(query, limit=limit * 2)
    vec_raw = semantic_search(query, limit=limit * 2)
    vec_results = _parse_vec_results(vec_raw)

    return _merge_ranked(fts_results, vec_results, limit)


def _pure_vector(query, limit):
    vec_raw = semantic_search(query, limit=limit)
    vec_ids = _parse_vec_results(vec_raw)
    ids = [msg_id for msg_id, _ in vec_ids]
    messages = get_messages_by_ids(ids)
    for m in messages:
        m["_source"] = "semantic"
        m["_score"] = _find_score(vec_ids, m["id"])
    return messages


def _pure_fts(query, limit):
    results = search_messages_fts(query, limit=limit)
    ids = [msg_id for msg_id, _ in results]
    messages = get_messages_by_ids(ids)
    for m in messages:
        m["_source"] = "keyword"
        m["_score"] = _find_score(results, m["id"])
    return messages


def _parse_vec_results(vec_raw):
    ids = vec_raw["ids"][0]
    dists = vec_raw["distances"][0]
    return [(int(i), d) for i, d in zip(ids, dists)]


def _find_score(pairs, target_id):
    for msg_id, score in pairs:
        if msg_id == target_id:
            return score
    return 0


def _merge_ranked(fts_results, vec_results, limit):
    fts_map = dict(fts_results)
    vec_map = dict(vec_results)

    if fts_map:
        fts_norm = {k: 2.0 / (1.0 + abs(v)) for k, v in fts_map.items()}
    else:
        fts_norm = {}

    if vec_map:
        dists = list(vec_map.values())
        max_dist = max(dists) if max(dists) > 0 else 1.0
        vec_norm = {k: 1.0 - (v / max_dist) for k, v in vec_map.items()}
    else:
        vec_norm = {}

    all_ids = set(fts_norm.keys()) | set(vec_norm.keys())
    scored = []
    for msg_id in all_ids:
        fts_score = fts_norm.get(msg_id, 0.0)
        vec_score = vec_norm.get(msg_id, 0.0)
        combined = 0.5 * fts_score + 0.5 * vec_score
        scored.append((msg_id, combined))

    scored.sort(key=lambda x: -x[1])
    top_ids = [msg_id for msg_id, _ in scored[:limit]]

    messages = get_messages_by_ids(top_ids)
    id_order = {msg_id: i for i, msg_id in enumerate(top_ids)}
    messages.sort(key=lambda m: id_order.get(m["id"], 999))

    for m in messages:
        m_id = m["id"]
        has_fts = m_id in fts_map
        has_vec = m_id in vec_map
        if has_fts and has_vec:
            m["_source"] = "hybrid"
        elif has_fts:
            m["_source"] = "keyword"
        else:
            m["_source"] = "semantic"
        m["_score"] = _find_score(scored, m_id)

    return messages
