# Copyright 2026 Alessio Mattoccia
"""Lexical include graph. This is deliberately NOT a complete call graph/AST."""
from pathlib import PurePosixPath
import re
import posixpath

def mask_comments(text: str) -> str:
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)

def graph(files: dict[str, str]):
    edges, external = [], []
    adjacency = {x: set() for x in files}
    for name, source in files.items():
        text = mask_comments(source)
        for match in re.finditer(r'^\s*#\s*include\s*([<"])([^>"\n]+)[>"]', text, re.M):
            include = match[2]
            candidates = [posixpath.normpath(str(PurePosixPath(name).parent / include)), include, 'include/' + include]
            target = next((x for x in candidates if x in files), None)
            if target:
                adjacency[name].add(target)
                edges.append({'source': name, 'target': target, 'line': text[:match.start()].count('\n') + 1})
            else:
                external.append({'source': name, 'include': include, 'kind': 'system_or_unresolved'})
    # Tarjan SCC, bounded by scanner's 1000-file limit; iterative reachability avoids recursion depth.
    reach = {}
    def reachable(start):
        if start in reach: return reach[start]
        todo, done = list(adjacency[start]), set()
        while todo:
            node = todo.pop()
            if node not in done:
                done.add(node); todo.extend(adjacency[node] - done)
        reach[start] = done
        return done
    cycles, visited = [], set()
    for node in adjacency:
        if node in visited: continue
        group = sorted(x for x in reachable(node) if node in reachable(x))
        if group:
            if node not in group: group.append(node); group.sort()
            cycles.append(group); visited.update(group)
    nodes = [{'id': x, 'incoming': sum(x in v for v in adjacency.values()), 'outgoing': len(adjacency[x])} for x in adjacency]
    return {'kind': 'lexical_include_graph', 'nodes': nodes, 'edges': edges, 'cycles': cycles,
            'most_connected': sorted(nodes, key=lambda n: (-n['incoming'] - n['outgoing'], n['id']))[:10],
            'unresolved': external,
            'limitations': ['Conditional preprocessor branches are not evaluated', 'Macro includes unresolved',
                            'Quoted includes resolved relative to file, root and include/ only; arbitrary compiler search order is not modeled',
                            'Not a call graph; no AST or link-time dependency analysis']}
