"""Bounded graph queries over the active corpus.

The store owns SQL. This module owns traversal, filtering, and path costs so
the same behavior can be reused by HTTP, workers, and later MCP tools.
"""

from __future__ import annotations

import heapq
import math
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol


class GraphReader(Protocol):
    def active_version(self) -> str | None: ...
    def node(self, node_id: str) -> dict[str, Any] | None: ...
    def outgoing_edges(
        self, src: str, *, edge_type: str | None = None, context_id: int | None = None
    ) -> list[dict[str, Any]]: ...
    def context_by_key(self, context: str) -> dict[str, Any] | None: ...
    def function_adjacency(self, context_id: int) -> list[dict[str, Any]]: ...
    def edges_between(
        self, src: str, dst: str, *, context_id: int | None = None
    ) -> list[dict[str, Any]]: ...


def node_id(value: str) -> str:
    """Accept the public function-token shorthand used by the workbench."""
    if value.startswith(("M:", "m:")):
        return f"function:{value}"
    return value


def _probability(edge: dict[str, Any]) -> float:
    value = edge.get("prob")
    return max(0.0, min(1.0, float(value))) if value is not None else 0.0


def _chromaticity(node: dict[str, Any] | None) -> float:
    if node is None:
        return 0.0
    props = node.get("props") or {}
    return float(props.get("chromaticity", 0.0))


_ADJACENCY_CACHE: OrderedDict[tuple[str, int], dict[str, list[dict[str, Any]]]] = OrderedDict()
_ADJACENCY_LOCK = Lock()


@dataclass
class GraphService:
    store: GraphReader
    # The module cache survives request-scoped store/session objects. Corpus
    # version is in the key, so activating a new version cannot serve old edges.
    cache_size: int = 8

    def _context_id(self, context: str) -> int:
        row = self.store.context_by_key(context)
        if row is None:
            raise ValueError(f"Unknown graph context: {context}")
        return int(row["id"])

    def get_node(self, value: str) -> dict[str, Any] | None:
        return self.store.node(node_id(value))

    def neighborhood(
        self,
        value: str,
        *,
        context: str = "global",
        edge_types: set[str] | None = None,
        min_prob: float = 0.0,
        limit: int = 100,
        hops: int = 1,
    ) -> dict[str, Any]:
        if hops not in (1, 2):
            raise ValueError("hops must be 1 or 2")
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if not 0 <= min_prob <= 1:
            raise ValueError("min_prob must be between 0 and 1")
        context_id = self._context_id(context)
        start = node_id(value)
        root = self.store.node(start)
        if root is None:
            raise LookupError(f"Graph node not found: {value}")

        nodes = {start: root}
        seen_edges: set[tuple[str, str, str, int]] = set()
        edges: list[dict[str, Any]] = []
        frontier = [start]
        for _ in range(hops):
            next_frontier: list[str] = []
            for src in frontier:
                candidates = self.store.outgoing_edges(src, context_id=context_id)
                candidates.sort(key=lambda edge: (-_probability(edge), str(edge["dst"])))
                for edge in candidates:
                    if edge_types and edge["type"] not in edge_types:
                        continue
                    if _probability(edge) < min_prob:
                        continue
                    key = (edge["src"], edge["dst"], edge["type"], edge["context_id"])
                    if key in seen_edges:
                        continue
                    seen_edges.add(key)
                    target = self.store.node(edge["dst"])
                    if target is None:
                        continue
                    nodes[edge["dst"]] = target
                    edges.append(edge)
                    if edge["dst"] not in frontier and edge["dst"] not in next_frontier:
                        next_frontier.append(edge["dst"])
                    if len(edges) >= limit:
                        return {"nodes": list(nodes.values()), "edges": edges, "context": context}
            frontier = next_frontier
            if not frontier:
                break
        return {"nodes": list(nodes.values()), "edges": edges, "context": context}

    def explain_edge(self, src: str, dst: str, *, context: str = "global") -> dict[str, Any]:
        context_id = self._context_id(context)
        source = node_id(src)
        target = node_id(dst)
        edges = self.store.edges_between(source, target, context_id=context_id)
        if not edges:
            raise LookupError(f"Graph edge not found: {src} → {dst}")
        fact_ids = sorted(
            {fact_id for edge in edges for fact_id in (edge.get("props") or {}).get("fact_ids", [])}
        )
        return {
            "source": self.store.node(source),
            "target": self.store.node(target),
            "edges": edges,
            "fact_ids": fact_ids,
            "evidence": {
                "count": sum(int(edge.get("count") or 0) for edge in edges),
                "support": sum(
                    int((edge.get("props") or {}).get("support") or 0) for edge in edges
                ),
            },
        }

    def _adjacency(self, context_id: int) -> dict[str, list[dict[str, Any]]]:
        version = self.store.active_version()
        if version is None:
            raise LookupError("No active corpus version")
        key = (version, context_id)
        with _ADJACENCY_LOCK:
            if key in _ADJACENCY_CACHE:
                _ADJACENCY_CACHE.move_to_end(key)
                return _ADJACENCY_CACHE[key]
        adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self.store.function_adjacency(context_id):
            if _probability(edge) > 0:
                adjacency[edge["src"]].append(edge)
        for outgoing in adjacency.values():
            outgoing.sort(key=lambda edge: (-_probability(edge), str(edge["dst"])))
        with _ADJACENCY_LOCK:
            _ADJACENCY_CACHE[key] = dict(adjacency)
            _ADJACENCY_CACHE.move_to_end(key)
            if len(_ADJACENCY_CACHE) > self.cache_size:
                _ADJACENCY_CACHE.popitem(last=False)
            return _ADJACENCY_CACHE[key]

    def paths(
        self,
        src: str,
        dst: str,
        *,
        context: str = "global",
        k: int = 3,
        max_len: int = 6,
        edge_types: set[str] | None = None,
        constraint: str = "none",
        max_chromaticity: float | None = None,
    ) -> list[dict[str, Any]]:
        if not 1 <= k <= 5 or not 1 <= max_len <= 6:
            raise ValueError("k must be 1–5 and max_len must be 1–6")
        if constraint not in {"none", "increasing_chromaticity", "max_chromaticity"}:
            raise ValueError("Invalid path constraint")
        if constraint == "max_chromaticity" and max_chromaticity is None:
            raise ValueError("max_chromaticity is required for that constraint")
        context_id = self._context_id(context)
        source, target = node_id(src), node_id(dst)
        if self.store.node(source) is None or self.store.node(target) is None:
            raise LookupError("Path endpoint not found")
        adjacency = self._adjacency(context_id)
        node_cache: dict[str, dict[str, Any] | None] = {}

        def get_node(identifier: str) -> dict[str, Any] | None:
            if identifier not in node_cache:
                node_cache[identifier] = self.store.node(identifier)
            return node_cache[identifier]

        # A bounded best-first search over simple paths. Positive edge costs
        # ensure the first k completed paths are the cheapest under this cost.
        queue: list[tuple[float, tuple[str, ...], tuple[dict[str, Any], ...]]] = [
            (0.0, (source,), ())
        ]
        results: list[dict[str, Any]] = []
        expansions = 0
        while queue and len(results) < k and expansions < 50_000:
            cost, nodes, edges = heapq.heappop(queue)
            if nodes[-1] == target and edges:
                results.append({"nodes": list(nodes), "edges": list(edges), "cost": cost})
                continue
            if len(edges) >= max_len:
                continue
            expansions += 1
            for edge in adjacency.get(nodes[-1], []):
                if edge_types and edge["type"] not in edge_types:
                    continue
                next_id = edge["dst"]
                if next_id in nodes:
                    continue
                next_chroma = _chromaticity(get_node(next_id))
                current_chroma = _chromaticity(get_node(nodes[-1]))
                if constraint == "increasing_chromaticity" and next_chroma < current_chroma:
                    continue
                if constraint == "max_chromaticity" and next_chroma > float(max_chromaticity):
                    continue
                edge_cost = -math.log(max(_probability(edge), 1e-12))
                if edge["type"] != "TRANSITIONS_TO":
                    edge_cost += 0.5
                heapq.heappush(queue, (cost + edge_cost, (*nodes, next_id), (*edges, edge)))
        return results
