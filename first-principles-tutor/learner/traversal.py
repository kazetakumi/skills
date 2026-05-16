#!/usr/bin/env python3
"""
Graph traversal for first-principles-tutor learner profile.
Usage:
  traversal.py owned                        — list all owned concepts
  traversal.py relevant <keyword> [...]     — concepts relevant to task keywords
  traversal.py prereqs <concept>            — all prerequisites of a concept
  traversal.py gaps                         — owned nodes with unowned dependencies
  traversal.py sequence <c1,c2,c3,...>      — order concepts by dependency, filter owned
  traversal.py baseline-check               — print upgraded baseline if thresholds met
"""

import json
import sys
from pathlib import Path
from collections import deque

GRAPH_PATH = Path(__file__).parent / "graph.json"
PROFILE_PATH = Path(__file__).parent / "profile.md"


def load_graph():
    if not GRAPH_PATH.exists():
        return {"nodes": [], "edges": [], "sequences": {}}
    return json.loads(GRAPH_PATH.read_text())


def save_graph(graph):
    GRAPH_PATH.write_text(json.dumps(graph, indent=2))


def nodes_by_id(graph):
    return {n["id"]: n for n in graph["nodes"]}


def edges_by_from(graph):
    result = {}
    for e in graph["edges"]:
        result.setdefault(e["from"], []).append(e)
    return result


def edges_by_to(graph):
    result = {}
    for e in graph["edges"]:
        result.setdefault(e["to"], []).append(e)
    return result


def cmd_owned(graph):
    owned = [n for n in graph["nodes"] if n["status"] == "owned"]
    for n in owned:
        print(f"{n['id']} ({n['domain']})")


def cmd_relevant(graph, keywords):
    keywords = [k.lower() for k in keywords]
    concepts_dir = Path(__file__).parent / "concepts"
    results = []
    for node in graph["nodes"]:
        # Load concept file summary and learned_in for richer matching
        concept_text = ""
        concept_file = concepts_dir / f"{node['id']}.md"
        if concept_file.exists():
            concept_text = concept_file.read_text().lower()

        searchable = " ".join([
            node["id"].lower(),
            node.get("domain", "").lower(),
            node.get("learned_in", "").lower(),
            concept_text,
        ])
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            results.append((score, node))
    results.sort(key=lambda x: -x[0])
    for _, node in results:
        print(f"{node['id']} ({node['domain']}) [{node['status']}]")


def cmd_prereqs(graph, concept):
    by_to = edges_by_to(graph)
    nodes = nodes_by_id(graph)
    visited = set()
    queue = deque([concept])
    prereqs = []
    while queue:
        current = queue.popleft()
        for edge in by_to.get(current, []):
            dep = edge["from"]
            if dep not in visited and edge["type"] == "depends_on":
                visited.add(dep)
                prereqs.append(dep)
                queue.append(dep)
    for p in prereqs:
        node = nodes.get(p, {})
        print(f"{p} ({node.get('domain', '?')}) [{node.get('status', 'not_owned')}]")


def cmd_gaps(graph):
    nodes = nodes_by_id(graph)
    by_to = edges_by_to(graph)
    for node in graph["nodes"]:
        if node["status"] == "owned":
            for edge in by_to.get(node["id"], []):
                dep = edge["from"]
                dep_node = nodes.get(dep)
                if dep_node and dep_node["status"] != "owned":
                    print(f"GAP: {node['id']} depends on {dep} which is not owned")


def cmd_sequence(graph, concepts_arg):
    concepts = [c.strip() for c in concepts_arg.split(",")]
    nodes = nodes_by_id(graph)
    by_to = edges_by_to(graph)

    # Filter out already owned
    to_teach = [c for c in concepts if nodes.get(c, {}).get("status") != "owned"]

    if not to_teach:
        print("ALL_OWNED")
        return

    # Topological sort by depends_on edges within the set
    in_set = set(to_teach)
    order = []
    visited = set()

    def visit(node):
        if node in visited or node not in in_set:
            return
        visited.add(node)
        for edge in by_to.get(node, []):
            if edge["type"] == "depends_on" and edge["from"] in in_set:
                visit(edge["from"])
        order.append(node)

    for c in to_teach:
        visit(c)

    for c in order:
        print(c)


def cmd_baseline_check(graph):
    profile_text = PROFILE_PATH.read_text() if PROFILE_PATH.exists() else ""
    current = "zero"
    for line in profile_text.splitlines():
        if line.startswith("baseline:"):
            current = line.split(":")[1].strip()

    owned = [n for n in graph["nodes"] if n["status"] == "owned"]
    domains = len(set(n.get("domain", "") for n in owned))
    count = len(owned)

    if count >= 15 and domains >= 3:
        new_level = "fluent"
    elif count >= 6 and domains >= 2:
        new_level = "partial"
    elif count >= 1:
        new_level = "surface"
    else:
        new_level = "zero"

    levels = ["zero", "surface", "partial", "fluent"]
    if levels.index(new_level) > levels.index(current):
        print(f"UPGRADE: {current} → {new_level}")
        # Update profile.md
        lines = profile_text.splitlines()
        updated = []
        for line in lines:
            if line.startswith("baseline:"):
                updated.append(f"baseline: {new_level}")
            else:
                updated.append(line)
        PROFILE_PATH.write_text("\n".join(updated))
    else:
        print(f"NO_CHANGE: {current}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    graph = load_graph()
    cmd = sys.argv[1]

    if cmd == "owned":
        cmd_owned(graph)
    elif cmd == "relevant":
        cmd_relevant(graph, sys.argv[2:])
    elif cmd == "prereqs":
        cmd_prereqs(graph, sys.argv[2])
    elif cmd == "gaps":
        cmd_gaps(graph)
    elif cmd == "sequence":
        cmd_sequence(graph, sys.argv[2])
    elif cmd == "baseline-check":
        cmd_baseline_check(graph)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
