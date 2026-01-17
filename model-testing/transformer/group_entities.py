from rapidfuzz import fuzz, process
from pprint import pprint
import itertools

def _get_similarity_list(strings, score_cutoff=0):
    results = {}
    for str1 in strings:
        for str2 in strings:
            if str1 != str2 and (str1, str2) not in results and (str2, str1) not in results:
                score = fuzz.WRatio(str1, str2, score_cutoff=score_cutoff)
                results[(str1, str2)] = score

    return results

def group_names(entities: list[str], score_cutoff=60) -> list[set]:
    """ Groups similar named entities together using fuzzy matching.
    Params:
    entities: list of named entity strings
    
    Returns:
    buckets: list of sets, each set containing similar named entities
    """
    buckets = []
    
    names = [t.replace(" ", "").lower() for t in entities]
    name_to_entity = dict(zip(names, entities))

    sim_list = _get_similarity_list(names, score_cutoff=score_cutoff)
    matches = [m[0] for m in list(sorted(sim_list.items(), key=lambda x: x[1], reverse=True)) if m[1] > 0]

    adj = {}
    for u, v in matches:
        if u not in adj: adj[u] = []
        if v not in adj: adj[v] = []
        adj[u].append(v)
        adj[v].append(u)
    
    visited = set()
    
    for node in adj:
        if node not in visited:
            component = set()
            stack = [node]
            visited.add(node)

            entity = name_to_entity[node]
            component.add(entity)
            while stack:
                curr = stack.pop()
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)

                        entity = name_to_entity[neighbor]
                        component.add(entity)
            buckets.append(component)

    rest = set(names) - visited
    for name in rest:
        buckets.append(set([name_to_entity[name]]))

    return buckets
