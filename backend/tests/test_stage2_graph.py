"""Stage 2 · Graph builder tests."""

from app.core.db import Database
from app.data.generator import DatasetGenerator, GeneratorConfig
from app.stage1.claim_analyzer import ClaimAnalyzer
from app.core.audit import AuditTrail
from app.stage2.graph_builder import GraphBuilder


def make_world(tmp_path, **kw):
    db = Database(str(tmp_path / "g.db"))
    cfg = GeneratorConfig(
        seed=kw.get("seed", 5), n_normal=kw.get("n_normal", 15),
        n_fraudsters=kw.get("n_fraudsters", 3), n_rings=kw.get("n_rings", 1),
        ring_size=kw.get("ring_size", 4), n_adversarial_rings=1,
        adversarial_ring_size=4, image_dir=str(tmp_path / "img"),
    )
    DatasetGenerator(db, cfg).generate()
    analyzer = ClaimAnalyzer(db, AuditTrail(db), enable_razorpay=False)
    return db, analyzer


def test_ring_members_are_fully_connected(tmp_path) -> None:
    db, analyzer = make_world(tmp_path)
    analyzer  # ensure stage1 results exist for pHash edges
    from app.data.generator import load_claims
    from app.stage1.claim_analyzer import build_claim_input
    from app.data.generator import load_orders

    orders = {o["order_id"]: o for o in load_orders(db)}
    for row in load_claims(db):
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    G = GraphBuilder(db).build()
    ring_nodes = [n for n, d in G.nodes(data=True)
                  if d.get("claims", 0) >= 1]
    assert ring_nodes

    # at least one dense clique of size >= 4 (the coordinated ring)
    import networkx as nx
    cliques = list(nx.find_cliques(G))
    assert any(len(c) >= 4 for c in cliques), "coordinated ring not fully connected"

    # edge attrs carry kind:entity pairs
    for _, _, data in G.edges(data=True):
        assert data["shared_types"]
        for pair in data["shared_entities"]:
            assert ":" in pair
        assert data["weight"] >= 1


def test_normal_customers_are_isolated(tmp_path) -> None:
    db, analyzer = make_world(tmp_path, n_normal=20)
    from app.data.generator import load_claims, load_orders, load_customers
    from app.stage1.claim_analyzer import build_claim_input

    orders = {o["order_id"]: o for o in load_orders(db)}
    for row in load_claims(db):
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    G = GraphBuilder(db).build()
    customers = {c["customer_id"]: c for c in load_customers(db)}
    normal_ids = [cid for cid, c in customers.items() if c["persona"] == "normal"]
    linked_normal = [n for n in normal_ids if n in G and G.degree(n) > 0]
    assert linked_normal == [], f"normal customers unexpectedly linked: {linked_normal}"


def test_nodes_carry_no_ground_truth(tmp_path) -> None:
    db, analyzer = make_world(tmp_path)
    from app.data.generator import load_claims, load_orders
    from app.stage1.claim_analyzer import build_claim_input

    orders = {o["order_id"]: o for o in load_orders(db)}
    for row in load_claims(db):
        analyzer.analyze(build_claim_input(row, orders.get(row["order_id"])))

    G = GraphBuilder(db).build()
    for _, attrs in G.nodes(data=True):
        assert "persona" not in attrs
        assert "ground_truth" not in attrs
        assert "ring_label" not in attrs
