"""Synthetic dataset generator.

Produces a seeded, labelled dataset with four customer populations:

1. ``normal``            – honest buyers, occasional genuine refunds
2. ``fraudster``         – individual abusers (image reuse, urgency, inflated claims)
3. ``ring``              – coordinated rings sharing device/address/bank, bursting
4. ``adversarial_ring``  – evasion-trained rings: shared bank only, spread-out timing

``ground_truth`` is stored ONLY for evaluation metrics. It is never exposed
to Stage 1/Stage 2 scorers — metrics stay honest by construction.
"""

from __future__ import annotations

import json
import logging
import random
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from app.core.audit import AuditTrail
from app.core.db import Database
from app.data.images import generate_evidence_image

logger = logging.getLogger("refundshield.generator")

PRODUCTS = [
    "wireless earbuds", "smartwatch", "running shoes", "backpack",
    "air fryer", "bluetooth speaker", "phone case", "water bottle",
    "yoga mat", "desk lamp", "gaming mouse", "coffee maker",
]

CITIES = ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai", "Jaipur"]

FIRST = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Sara", "Vikram", "Anaya",
         "Ishaan", "Priya", "Arjun", "Neha", "Dev", "Tara", "Kunal", "Riya",
         "Aditya", "Zoya", "Manav", "Kiara", "Sameer", "Ira", "Yash", "Naina"]

LAST = ["Sharma", "Patel", "Iyer", "Khan", "Reddy", "Gupta", "Mehta", "Singh",
        "Das", "Kulkarni", "Joshi", "Verma", "Nair", "Bose", "Rao", "Shah"]

LEGIT_TEXTS = [
    "The {product} arrived with a small crack on the corner. Packaging was "
    "fine, so it may have happened before shipping. Would like a refund please.",
    "Ordered the {product} in size M but it doesn't fit. Tag is still on, "
    "happy to return it for a refund.",
    "Hi, I received the wrong colour for my {product}. I ordered black but "
    "got white. Requesting a refund, I can return the item.",
    "The {product} stopped working after two days. I've attached a photo of "
    "the error. Please process a refund.",
    "Changed my mind about the {product}, it's unopened and sealed. "
    "Returning it within the window.",
    "The {product} doesn't match the description on the website — the "
    "material feels different. I'd like to return it.",
]

FRAUD_TEXTS = [
    "This is unacceptable. Refund my money NOW or I will file a chargeback "
    "and a consumer court case today itself.",
    "Item NEVER arrived and nobody is responding. I want a full refund "
    "immediately or I'm calling my bank and posting this everywhere online.",
    "Worst product ever, complete scam. Give me my refund or I will file a "
    "police complaint and dispute the payment with my bank.",
    "Refund immediately. I have already contacted a lawyer. If money is not "
    "returned in 24 hours I will escalate on social media and to the press.",
    "I demand a full refund TODAY. Do not make me do a chargeback — that "
    "will cost you more. Attach photo as proof.",
    "Product is damaged and useless. Refund the FULL amount including "
    "shipping or face a formal complaint. Acting on this today.",
]

RING_TEXTS = [
    "The {product} never arrived even though tracking says delivered. "
    "This is theft. Full refund immediately or chargeback + consumer case.",
    "Package was EMPTY when it arrived — this is fraud by the seller. "
    "Refund the full amount today or I escalate to my bank and the police.",
    "Item missing from delivery, only the box came. I demand my money back "
    "NOW. Will file police complaint and chargeback if ignored.",
]

ADVERSARIAL_TEXTS = [
    "Hi, I think there was an issue with my delivery of the {product}. "
    "Could you check and process a refund if it wasn't delivered?",
    "The {product} I ordered seems to have gone missing in transit. "
    "I'd appreciate a refund when you get a chance.",
    "Facing a delivery problem with my {product} order. Requesting a "
    "refund — happy to share any details needed.",
    "My {product} order shows delivered but I haven't received it. "
    "Please look into it and refund if it's lost.",
]


class GeneratorConfig(BaseModel):
    seed: int = 42
    n_normal: int = 120
    n_fraudsters: int = 15
    n_rings: int = 3
    ring_size: int = 5
    n_adversarial_rings: int = 1
    adversarial_ring_size: int = 6
    image_dir: str = "./synthetic_images"


class DatasetSummary(BaseModel):
    seed: int
    customers_by_persona: dict[str, int]
    total_orders: int = 0
    total_claims: int = 0
    fraudulent_claims: int = 0
    legit_claims: int = 0
    images_created: int = 0
    rings: list[dict] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetGenerator:
    def __init__(self, db: Database, config: GeneratorConfig | None = None) -> None:
        self.db = db
        self.config = config or GeneratorConfig()
        self.rng = random.Random(self.config.seed)
        self.image_root = Path(self.config.image_dir)
        self._seq = {"customer": 0, "order": 10000, "claim": 20000}
        self._images_created = 0

    # ------------------------------------------------------------ id helpers
    def _next(self, kind: str, prefix: str) -> str:
        self._seq[kind] += 1
        return f"{prefix}{self._seq[kind]:05d}"

    def _person(self) -> tuple[str, str]:
        return self.rng.choice(FIRST), self.rng.choice(LAST)

    def _dt(self, dt: datetime) -> str:
        return dt.isoformat()

    # ------------------------------------------------------------ image helper
    def _new_evidence(self, seed_key: str, kind: str = "unique",
                      source: str | None = None) -> str:
        path = self.image_root / f"ev_{seed_key}_{self._images_created}.png"
        # crc32 (not hash()) for cross-process determinism
        generate_evidence_image(path, seed=zlib.crc32(seed_key.encode()), kind=kind,
                                source_path=source)
        self._images_created += 1
        return str(path)

    # ------------------------------------------------------------ populations
    def _normal_customer(self, now: datetime) -> dict:
        cid = self._next("customer", "CUST-")
        first, last = self._person()
        created = now - timedelta(days=self.rng.randint(200, 900))
        return {
            "customer_id": cid, "persona": "normal",
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{self._seq['customer']}@example.com",
            "created_at": self._dt(created), "ring_label": None,
        }

    def _fraudster(self, now: datetime) -> dict:
        cid = self._next("customer", "CUST-")
        first, last = self._person()
        created = now - timedelta(days=self.rng.randint(3, 60))
        return {
            "customer_id": cid, "persona": "fraudster",
            "name": f"{first} {last}",
            "email": f"{first.lower()}{self._seq['customer']}@maildrop.example",
            "created_at": self._dt(created), "ring_label": None,
        }

    def _ring_member(self, now: datetime, ring_label: str,
                     persona: str) -> dict:
        cid = self._next("customer", "CUST-")
        first, last = self._person()
        created = now - timedelta(days=self.rng.randint(10, 120))
        return {
            "customer_id": cid, "persona": persona,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{self._seq['customer']}@example.com",
            "created_at": self._dt(created), "ring_label": ring_label,
        }

    # ------------------------------------------------------------ orders
    def _make_order(self, customer: dict, when: datetime, device: str,
                    address: str, delivered: bool) -> dict:
        amount = self.rng.choice([49900, 79900, 99900, 129900, 149900, 199900, 249900])
        delivered_at = (
            when + timedelta(days=self.rng.randint(2, 7)) if delivered else None
        )
        return {
            "order_id": self._next("order", "ORD-"),
            "customer_id": customer["customer_id"],
            "amount_paise": amount,
            "status": "paid",
            "device_id": device,
            "address_id": address,
            "created_at": self._dt(when),
            "delivered_at": self._dt(delivered_at) if delivered_at else None,
            "payment_id": None,
            "source": "simulated",
            "notes_json": json.dumps({}),
        }

    # ------------------------------------------------------------ claims
    def _legit_claim(self, customer: dict, order: dict, now: datetime) -> dict | None:
        if order["delivered_at"] is None:
            return None
        delivered = datetime.fromisoformat(order["delivered_at"])
        claimed_at = delivered + timedelta(days=self.rng.randint(2, 10))
        if claimed_at > now:
            return None
        product = self.rng.choice(PRODUCTS)
        text = self.rng.choice(LEGIT_TEXTS).format(product=product)
        image = self._new_evidence(f"{order['order_id']}_legit", "unique")
        return self._claim_row(customer, order, text, order["amount_paise"],
                               image, claimed_at, ground_truth=0)

    def _fraud_claim(self, customer: dict, order: dict,
                     evidence_pool: list[str], now: datetime) -> dict:
        product = self.rng.choice(PRODUCTS)
        if self.rng.random() < 0.4 and order["delivered_at"] is not None:
            # claim while still 'in transit'
            claimed_at = datetime.fromisoformat(order["created_at"]) + timedelta(
                hours=self.rng.randint(20, 48))
        else:
            base = order["delivered_at"] or order["created_at"]
            claimed_at = datetime.fromisoformat(base) + timedelta(
                hours=self.rng.randint(4, 30))
        claimed_at = min(claimed_at, now)

        if evidence_pool and self.rng.random() < 0.7:
            src = self.rng.choice(evidence_pool)
            kind = self.rng.choice(["copy", "noise", "recolor"])
            image = self._new_evidence(f"{order['order_id']}_fraud", kind, source=src)
        else:
            image = self._new_evidence(f"{order['order_id']}_fraud", "ai")

        amount = order["amount_paise"]
        if self.rng.random() < 0.3:
            amount = int(amount * self.rng.uniform(1.1, 1.8))
        text = self.rng.choice(FRAUD_TEXTS).format(product=product)
        return self._claim_row(customer, order, text, amount, image,
                               claimed_at, ground_truth=1)

    def _ring_claim(self, customer: dict, order: dict, text: str,
                    ring_image: str, burst_anchor: datetime) -> dict:
        offset = timedelta(hours=self.rng.randint(-36, 36))
        claimed_at = burst_anchor + offset
        return self._claim_row(customer, order, text.format(
            product=self.rng.choice(PRODUCTS)), order["amount_paise"],
            ring_image, claimed_at, ground_truth=1)

    def _adversarial_claim(self, customer: dict, order: dict,
                           text: str, now: datetime) -> dict:
        kind = "ai" if self.rng.random() < 0.3 else "unique"
        image = self._new_evidence(f"{order['order_id']}_adv", kind)
        claimed_at = min(datetime.fromisoformat(order["created_at"]) +
                         timedelta(days=self.rng.randint(4, 9)), now)
        return self._claim_row(customer, order, text.format(
            product=self.rng.choice(PRODUCTS)), order["amount_paise"],
            image, claimed_at, ground_truth=1)

    def _claim_row(self, customer: dict, order: dict, text: str,
                   amount_paise: int, image: str, claimed_at: datetime,
                   *, ground_truth: int) -> dict:
        return {
            "claim_id": self._next("claim", "CLM-"),
            "order_id": order["order_id"],
            "customer_id": customer["customer_id"],
            "text": text,
            "amount_paise": amount_paise,
            "image_path": image,
            "created_at": self._dt(claimed_at),
            "persona": customer["persona"],
            "ring_label": customer["ring_label"],
            "ground_truth": ground_truth,
            "status": "open",
        }

    # ------------------------------------------------------------ persistence
    def _insert_order(self, o: dict) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO orders (order_id, customer_id, amount_paise, status,
                   device_id, address_id, created_at, delivered_at, payment_id,
                   source, notes_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (o["order_id"], o["customer_id"], o["amount_paise"], o["status"],
                 o["device_id"], o["address_id"], o["created_at"],
                 o["delivered_at"], o["payment_id"], o["source"], o["notes_json"]),
            )

    def _insert_claim(self, c: dict) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO claims (claim_id, order_id, customer_id, text,
                   amount_paise, image_path, created_at, persona, ring_label,
                   ground_truth, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["claim_id"], c["order_id"], c["customer_id"], c["text"],
                 c["amount_paise"], c["image_path"], c["created_at"],
                 c["persona"], c["ring_label"], c["ground_truth"], c["status"]),
            )

    def _insert_customer(self, c: dict, vpas: list[str]) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO customers (customer_id, persona, name, email,
                   created_at, ring_label) VALUES (?, ?, ?, ?, ?, ?)""",
                (c["customer_id"], c["persona"], c["name"], c["email"],
                 c["created_at"], c["ring_label"]),
            )
            for vpa in vpas:
                conn.execute(
                    "INSERT OR IGNORE INTO bank_accounts (customer_id, vpa) VALUES (?, ?)",
                    (c["customer_id"], vpa),
                )

    # ------------------------------------------------------------ main entry
    def generate(self) -> DatasetSummary:
        cfg = self.config
        now = datetime.now(timezone.utc)
        counts: dict[str, int] = {"normal": 0, "fraudster": 0,
                                  "ring": 0, "adversarial_ring": 0}
        orders: list[dict] = []
        claims: list[dict] = []
        rings_meta: list[dict] = []

        # ---- 1. normal customers ----
        for _ in range(cfg.n_normal):
            cust = self._normal_customer(now)
            counts["normal"] += 1
            device = f"DEV-N{self._seq['customer']:05d}"
            address = f"ADDR-N{self._seq['customer']:05d}"
            vpa = f"{cust['customer_id'].lower()}@okbank"
            self._insert_customer(cust, [vpa])

            n_orders = self.rng.randint(1, 4)
            cust_orders: list[dict] = []
            base_days = self.rng.randint(60, 800)
            for _ in range(n_orders):
                when = now - timedelta(days=self.rng.randint(20, base_days))
                o = self._make_order(cust, when, device, address, delivered=True)
                self._insert_order(o)
                orders.append(o)
                cust_orders.append(o)

            if cust_orders and self.rng.random() < 0.25:
                o = self.rng.choice(cust_orders[-2:] if len(cust_orders) > 1
                                    else cust_orders)
                c = self._legit_claim(cust, o, now)
                if c:
                    self._insert_claim(c)
                    claims.append(c)

        # ---- 2. individual fraudsters ----
        for _ in range(cfg.n_fraudsters):
            cust = self._fraudster(now)
            counts["fraudster"] += 1
            device = f"DEV-F{self._seq['customer']:05d}"
            address = f"ADDR-F{self._seq['customer']:05d}"
            vpa = f"quickcash.{self._seq['customer']}@upi"
            self._insert_customer(cust, [vpa])

            n_orders = self.rng.randint(3, 7)
            evidence_pool: list[str] = []
            first_order_day = self.rng.randint(5, 40)
            for i in range(n_orders):
                when = now - timedelta(days=first_order_day - i * self.rng.randint(0, 3))
                o = self._make_order(cust, when, device, address,
                                     delivered=self.rng.random() < 0.85)
                self._insert_order(o)
                orders.append(o)
                if self.rng.random() < 0.9:
                    c = self._fraud_claim(cust, o, evidence_pool, now)
                    self._insert_claim(c)
                    claims.append(c)
                    if c["image_path"]:
                        evidence_pool.append(c["image_path"])

        # ---- 3. coordinated rings (bursty, shared device+address+VPA) ----
        for r in range(cfg.n_rings):
            ring_label = f"ring-{r + 1}"
            shared_device = f"DEV-R{r + 1}00"
            shared_addr = f"ADDR-R{r + 1}00"
            shared_vpa = f"circle.{r + 1}@upi"
            members: list[dict] = []
            for _ in range(cfg.ring_size):
                m = self._ring_member(now, ring_label, "ring")
                counts["ring"] += 1
                self._insert_customer(m, [shared_vpa])
                members.append(m)

            burst_anchor = now - timedelta(days=self.rng.randint(3, 30),
                                           hours=self.rng.randint(0, 12))
            ring_image = self._new_evidence(f"{ring_label}_shared", "unique")
            text = self.rng.choice(RING_TEXTS)

            for m in members:
                o = self._make_order(m, burst_anchor - timedelta(days=5, hours=12),
                                     shared_device, shared_addr, delivered=True)
                self._insert_order(o)
                orders.append(o)
                c = self._ring_claim(m, o, text, ring_image, burst_anchor)
                self._insert_claim(c)
                claims.append(c)
            rings_meta.append({
                "ring_label": ring_label, "persona": "ring",
                "size": len(members), "shared_entities": [
                    shared_device, shared_addr, shared_vpa],
            })

        # ---- 4. adversarial rings (bank-only link, spread timing) ----
        for r in range(cfg.n_adversarial_rings):
            ring_label = f"adv-ring-{r + 1}"
            shared_vpa = f"silent.{r + 1}@upi"
            members: list[dict] = []
            for _ in range(cfg.adversarial_ring_size):
                m = self._ring_member(now, ring_label, "adversarial_ring")
                counts["adversarial_ring"] += 1
                self._insert_customer(m, [shared_vpa])
                members.append(m)

            start_day = self.rng.randint(10, 40)
            for i, m in enumerate(members):
                device = f"DEV-A{r + 1}{i:02d}"
                address = f"ADDR-A{r + 1}{i:02d}"
                when = now - timedelta(days=start_day - i * self.rng.randint(2, 5))
                o = self._make_order(m, when, device, address, delivered=True)
                self._insert_order(o)
                orders.append(o)
                text = ADVERSARIAL_TEXTS[i % len(ADVERSARIAL_TEXTS)]
                c = self._adversarial_claim(m, o, text, now)
                self._insert_claim(c)
                claims.append(c)
            rings_meta.append({
                "ring_label": ring_label, "persona": "adversarial_ring",
                "size": len(members), "shared_entities": [shared_vpa],
            })

        summary = DatasetSummary(
            seed=cfg.seed,
            customers_by_persona=counts,
            total_orders=len(orders),
            total_claims=len(claims),
            fraudulent_claims=sum(1 for c in claims if c["ground_truth"] == 1),
            legit_claims=sum(1 for c in claims if c["ground_truth"] == 0),
            images_created=self._images_created,
            rings=rings_meta,
        )
        AuditTrail(self.db).record(
            event_type="data.generate",
            actor="generator",
            subject_type="dataset",
            subject_id=f"seed-{cfg.seed}",
            summary=(f"Generated {summary.total_claims} claims "
                     f"({summary.fraudulent_claims} fraudulent) from "
                     f"{len(counts)} persona groups"),
            payload=summary.model_dump(mode="json"),
        )
        logger.info("Dataset generated: %s", summary.model_dump_json(indent=2)[:400])
        return summary


# ------------------------------------------------------------------ readers
def load_customers(db: Database) -> list[dict]:
    with db.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM customers").fetchall()]


def load_orders(db: Database) -> list[dict]:
    with db.connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM orders").fetchall()]


def load_claims(db: Database, status: str | None = None) -> list[dict]:
    query = "SELECT * FROM claims"
    params: tuple = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)
    with db.connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def load_bank_accounts(db: Database) -> dict[str, list[str]]:
    with db.connect() as conn:
        rows = conn.execute("SELECT customer_id, vpa FROM bank_accounts").fetchall()
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["customer_id"], []).append(r["vpa"])
    return out


def iter_open_claims(db: Database) -> Iterator[dict]:
    yield from load_claims(db, status="open")
