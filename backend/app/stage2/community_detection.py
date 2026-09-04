"""Stage 2 · Louvain community detection.

Communities are candidates; each candidate is then split into connected
components so that two genuinely separate rings weakly bridged by one
edge are not merged into a single fake super-ring.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import community as community_louvain
import networkx as nx

logger = logging.getLogger("refundshield.stage2.community")


class CommunityDetector:
    def __init__(self, resolution: float = 1.0, seed: int = 42) -> None:
        self.resolution = resolution
        self.seed = seed

    def detect(self, G: nx.Graph) -> tuple[list[list[str]], float | None]:
        """Return (communities, modularity). Deterministic via seed."""
        if G.number_of_nodes() == 0:
            return [], None

        partition = community_louvain.best_partition(
            G,
            weight="weight",
            resolution=self.resolution,
            random_state=self.seed,
            randomize=False,
        )
        modularity: float | None = None
        try:
            modularity = community_louvain.modularity(
                partition, G, weight="weight")
        except (ZeroDivisionError, ValueError):
            modularity = None

        buckets: dict[int, list[str]] = defaultdict(list)
        for node, comm in partition.items():
            buckets[comm].append(node)

        communities: list[list[str]] = []
        for members in buckets.values():
            if len(members) < 2:
                continue  # singletons are not rings
            sub = G.subgraph(members)
            for component in nx.connected_components(sub):
                if len(component) >= 2:
                    communities.append(sorted(component))

        communities.sort(key=len, reverse=True)
        logger.info("Louvain: %d ring candidates (modularity=%s)",
                    len(communities), modularity)
        return communities, modularity
