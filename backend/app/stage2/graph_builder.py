"""Stage 2 · Graph construction.

Nodes are customers. Edges are created when two customers share a
refund-destination or identity entity:

- ``device``  – same device fingerprint on orders
- ``address`` – same shipping address on orders
- ``vpa``     – same bank VPA (refund destination)
- ``image``   – identical perceptual hash on submitted claim evidence

Node attributes carry Stage 1 aggregates ONLY (avg risk, claim count,
claimed ₹). Personas / ground-truth labels are never attached.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict

import networkx as nx

from app.core.db import Database

logger = logging.getLogger("refundshield.stage2.graph")

ENTITY_KINDS = ("device", "address", "vpa", "image")


class GraphBuilder:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------ API
    def build(self) -> nx.Graph:
        G = nx.Graph()
        risk_by_customer = self._stage1_risk_by_customer()
        claims_by_customer = self._claims_by_customer()

        for customer_id, agg in risk_by_customer.items():
            G.add_node(
                customer_id,
                avg_stage1_risk=agg["avg_risk"],
                claims=agg["claims"],
                total_claimed_inr=agg["total_claimed_inr"],
            )
        for customer_id, (n_claims, amount) in claims_by_customer.items():
            if customer_id not in G:
                G.add_node(
                    customer_id,
                    avg_stage1_risk=0.0,
                    claims=n_claims,
                    total_claimed_inr=amount,
                )

        for kind, entity_id, members in self._entity_groups():
            for i, a in enumerate(members):
                for b in members[i + 1:]:
                    if G.has_edge(a, b):
                        G[a][b]["shared_types"].add(kind)
                        G[a][b]["shared_pairs"].add(f"{kind}:{entity_id}")
                    else:
                        G.add_edge(
                            a, b,
                            shared_types={kind},
                            shared_pairs={f"{kind}:{entity_id}"},
                        )

        for _, _, data in G.edges(data=True):
            data["weight"] = len(data["shared_types"])
            data["shared_types"] = sorted(data["shared_types"])
            # keep kind:entity pairs together so grouping stays correct
            data["shared_entities"] = sorted(data["shared_pairs"])

        logger.info(
            "Graph built: %d nodes, %d edges", G.number_of_nodes(),
            G.number_of_edges())
        return G

    # -------------------------------------------------------------- loaders
    def _stage1_risk_by_customer(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT customer_id, risk_score, payload_json FROM claim_results"
            ).fetchall()
        for r in rows:
            entry = out.setdefault(r["customer_id"], {
                "risks": [], "claims": 0, "total_claimed_inr": 0.0,
            })
            entry["risks"].append(r["risk_score"])
            entry["claims"] += 1
            try:
                payload = json.loads(r["payload_json"])
                entry["total_claimed_inr"] += payload.get(
                    "payment_delivery_evidence", {}).get("amount_claimed_inr", 0.0)
            except (json.JSONDecodeError, AttributeError):
                pass
        for entry in out.values():
            entry["avg_risk"] = round(sum(entry["risks"]) / len(entry["risks"]), 3)
        return out

    def _claims_by_customer(self) -> dict[str, tuple[int, float]]:
        out: dict[str, tuple[int, float]] = {}
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT customer_id, amount_paise FROM claims"
            ).fetchall()
        for r in rows:
            n, total = out.get(r["customer_id"], (0, 0.0))
            out[r["customer_id"]] = (n + 1, total + r["amount_paise"] / 100.0)
        return out

    def _entity_groups(self) -> list[tuple[str, str, list[str]]]:
        groups: list[tuple[str, str, list[str]]] = []

        with self.db.connect() as conn:
            for kind, table, col in (
                ("device", "orders", "device_id"),
                ("address", "orders", "address_id"),
            ):
                rows = conn.execute(
                    f"SELECT {col} AS e, customer_id FROM {table} "
                    f"GROUP BY {col}, customer_id"
                ).fetchall()
                buckets: dict[str, list[str]] = defaultdict(list)
                for r in rows:
                    buckets[r["e"]].append(r["customer_id"])
                for entity_id, members in buckets.items():
                    if len(members) >= 2:
                        groups.append((kind, entity_id, sorted(members)))

            rows = conn.execute(
                "SELECT vpa, customer_id FROM bank_accounts"
            ).fetchall()
            vpa_buckets: dict[str, list[str]] = defaultdict(list)
            for r in rows:
                vpa_buckets[r["vpa"]].append(r["customer_id"])
            for entity_id, members in vpa_buckets.items():
                if len(members) >= 2:
                    groups.append(("vpa", entity_id, sorted(members)))

            rows = conn.execute(
                """SELECT customer_id, payload_json FROM claim_results
                   WHERE payload_json LIKE '%perceptual_hash%'"""
            ).fetchall()
        img_buckets: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            try:
                ph = json.loads(r["payload_json"]).get(
                    "image_evidence", {}).get("perceptual_hash")
                if ph:
                    img_buckets[ph].append(r["customer_id"])
            except (json.JSONDecodeError, AttributeError):
                continue
        for entity_id, members in img_buckets.items():
            if len(members) >= 2:
                groups.append(("image", f"phash:{entity_id[:12]}",
                               sorted(set(members))))
        return groups
