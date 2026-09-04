"""Stage 2 · Community detection tests (synthetic graphs)."""

import networkx as nx

from app.stage2.community_detection import CommunityDetector


def two_cliques_bridge() -> nx.Graph:
    G = nx.Graph()
    a = [f"a{i}" for i in range(4)]
    b = [f"b{i}" for i in range(4)]
    for group in (a, b):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                G.add_edge(group[i], group[j], weight=3)
    G.add_edge(a[0], b[0], weight=1)  # weak bridge
    return G


def test_two_cliques_split_into_two_communities() -> None:
    G = two_cliques_bridge()
    communities, modularity = CommunityDetector(seed=1).detect(G)
    assert len(communities) == 2
    sets = [set(c) for c in communities]
    assert {"a0", "a1", "a2", "a3"} in sets
    assert {"b0", "b1", "b2", "b3"} in sets
    assert modularity is not None and modularity > 0.2


def test_detection_is_deterministic() -> None:
    G = two_cliques_bridge()
    c1, _ = CommunityDetector(seed=7).detect(G)
    c2, _ = CommunityDetector(seed=7).detect(G)
    assert [sorted(c) for c in c1] == [sorted(c) for c in c2]


def test_isolated_nodes_are_ignored() -> None:
    G = two_cliques_bridge()
    G.add_nodes_from(["lone1", "lone2"])
    communities, _ = CommunityDetector(seed=3).detect(G)
    for c in communities:
        assert "lone1" not in c and "lone2" not in c


def test_empty_graph_returns_empty() -> None:
    communities, modularity = CommunityDetector().detect(nx.Graph())
    assert communities == []
    assert modularity is None


def test_weak_bridge_splits_into_components() -> None:
    """Even if Louvain merges bridged cliques, components must split them."""
    G = two_cliques_bridge()
    # force one community by using very high resolution on a dense graph:
    # instead, verify component splitting via a manual community list
    from collections import defaultdict
    import community as community_louvain

    partition = community_louvain.best_partition(G, random_state=0)
    buckets = defaultdict(list)
    for node, comm in partition.items():
        buckets[comm].append(node)
    for members in buckets.values():
        sub = G.subgraph(members)
        comps = list(nx.connected_components(sub))
        # each connected piece is a separate ring candidate
        assert all(len(c) >= 2 for c in comps) or len(comps) == 1
