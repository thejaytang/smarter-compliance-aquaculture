"""Capacity checks for original occurrences sharing spatial output candidates.

Output token occurrences may be used once per evidence engine, never once per
overlapping original line. This is a coverage constraint, not a structural or
semantic alignment claim. Separate engines remain alternative observations.
"""
from collections import Counter, deque


def _maximum_assignment(demands, supplies, neighbors):
    graph = {}
    source, sink = ('source',), ('sink',)

    def edge(a, b, capacity):
        graph.setdefault(a, {})[b] = capacity
        graph.setdefault(b, {})[a] = 0

    for line, count in demands.items():
        edge(source, ('line', line), count)
        for record in neighbors[line]:
            if supplies.get(record, 0):
                edge(('line', line), ('record', record), count)
    for record, count in supplies.items():
        if count:
            edge(('record', record), sink, count)
    matched = 0
    while True:
        parent = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for target, capacity in graph[node].items():
                if capacity > 0 and target not in parent:
                    parent[target] = node
                    queue.append(target)
        if sink not in parent:
            return matched
        amount = sum(demands.values())
        node = sink
        while parent[node] is not None:
            previous = parent[node]
            amount = min(amount, graph[previous][node])
            node = previous
        node = sink
        while parent[node] is not None:
            previous = parent[node]
            graph[previous][node] -= amount
            graph[node][previous] += amount
            node = previous
        matched += amount


def shortfalls(lines, positioned, tokenize, overlap):
    observed = [Counter(tokenize(record['text'])) for record, _ in positioned]
    required = [Counter(tokenize(line['text'])) for line in lines]
    neighbors = {i: [r for r, (_, bounds) in enumerate(positioned)
                     if any(overlap(line['bbox'], b) for b in bounds)]
                 for i, line in enumerate(lines)}
    engines = {}
    for i, line in enumerate(lines):
        engines.setdefault(line['engine'], []).append(i)
    results = []
    for engine, indices in engines.items():
        vocabulary = sorted({token for i in indices for token in required[i]})
        for token in vocabulary:
            demands = {i: required[i][token] for i in indices if required[i][token]}
            # A sole original line is already checked by the direct comparator.
            if len(demands) < 2:
                continue
            candidates = {r for i in demands for r in neighbors[i]}
            supplies = {r: observed[r][token] for r in candidates if observed[r][token]}
            matched = _maximum_assignment(demands, supplies, neighbors)
            needed = sum(demands.values())
            if matched < needed:
                results.append(dict(token=token, engine=engine, required_occurrences=needed,
                                    matched_occurrences=matched, missing_occurrences=needed-matched,
                                    source_line_indices=list(demands),
                                    output_indices=sorted(candidates)))
    return results
