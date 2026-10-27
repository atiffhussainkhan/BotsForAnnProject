"""
Grounded Fragrance Knowledge Base (`fragrance_kb.py`) for Ann Reveals AI Manager (v4.0).

Implements FR-008, FR-018, FR-019, FR-020, FR-021, FR-022, FR-051, FR-052, FR-054:
- Stores verified perfume records with top/heart/base notes, concentration, and scent profiles.
- Explicitly distinguishes fragrances where Ann has measured wear-time (`wear_time_measured=True`)
  from unmeasured items (`wear_time_measured=False`, `wear_time_hours=None`).
- Preserves raw OCR store labels (`Experian` vs `Empyrean`) and refuses to surface unverified
  raw OCR merchant names as public stockists until `store_verified=True`.
- Keeps `acquisition_source` (`SELF_PURCHASED`, `PR_GIFTED`, `LOANED`, `UNKNOWN`) separate from
  `commercial_relationship` (`NONE`, `AFFILIATE`, `PAID_COLLAB`, `TIKTOK_SHOP`, `GIFTED_INCENTIVE`).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


VALID_ACQUISITION_SOURCES = frozenset({
    "SELF_PURCHASED",
    "PR_GIFTED",
    "LOANED",
    "UNKNOWN",
})

VALID_COMMERCIAL_RELATIONSHIPS = frozenset({
    "NONE",
    "AFFILIATE",
    "PAID_COLLAB",
    "TIKTOK_SHOP",
    "GIFTED_INCENTIVE",
})


@dataclass(frozen=True)
class FragranceRecord:
    """Immutable grounded record for a perfume in Ann's collection."""

    sku: str
    product_name: str
    brand: str
    variant: str
    size_ml: int
    concentration: str
    top_notes: Tuple[str, ...]
    heart_notes: Tuple[str, ...]
    base_notes: Tuple[str, ...]
    scent_family: str
    vibe_summary: str
    wear_time_measured: bool
    wear_time_hours: Optional[Tuple[int, int]] = None
    sillage_profile: Optional[str] = None
    public_price_gbp: Optional[float] = None
    canonical_store: Optional[str] = None
    raw_store_label: Optional[str] = None
    store_verified: bool = True
    acquisition_source: str = "SELF_PURCHASED"
    commercial_relationship: str = "NONE"
    owner_confirmed: bool = True
    evidence_id: str = ""
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.acquisition_source not in VALID_ACQUISITION_SOURCES:
            raise ValueError(f"Invalid acquisition_source: {self.acquisition_source}")
        if self.commercial_relationship not in VALID_COMMERCIAL_RELATIONSHIPS:
            raise ValueError(f"Invalid commercial_relationship: {self.commercial_relationship}")
        if self.wear_time_measured and not self.wear_time_hours:
            raise ValueError("wear_time_hours must be provided when wear_time_measured is True")
        if not self.wear_time_measured and self.wear_time_hours is not None:
            raise ValueError("wear_time_hours must be None when wear_time_measured is False")

    @property
    def all_notes(self) -> Tuple[str, ...]:
        return self.top_notes + self.heart_notes + self.base_notes

    @property
    def has_commercial_incentive(self) -> bool:
        """True if any affiliate, TikTok Shop, paid collab, or gifted incentive exists."""
        return self.commercial_relationship != "NONE" or self.acquisition_source == "PR_GIFTED"

    def safe_public_store_name(self) -> Optional[str]:
        """
        Return the verified store name for public replies.
        Never exposes unconfirmed raw OCR strings like 'Experian' as a perfume retailer (FR-019).
        """
        if not self.store_verified:
            return None
        if self.canonical_store and self.canonical_store.strip().lower() == "experian":
            return None
        return self.canonical_store

    def formatted_notes_summary(self) -> str:
        """Return a concise UK English summary of verified notes."""
        top = ", ".join(self.top_notes[:2])
        heart = ", ".join(self.heart_notes[:2])
        base = ", ".join(self.base_notes[:2])
        return f"It opens with {top}, moves into a heart of {heart}, and settles into {base} in the dry-down"

    def formatted_longevity_statement(self) -> str:
        """
        Return a strictly grounded wear-time statement (FR-008).
        Never fabricates hours when wear_time_measured is False.
        """
        if self.wear_time_measured and self.wear_time_hours is not None:
            low, high = self.wear_time_hours
            sillage_part = f" with a {self.sillage_profile}" if self.sillage_profile else ""
            return (
                f"On my skin, {self.product_name} lasts around {low} to {high} hours"
                f"{sillage_part}."
            )
        return (
            f"I haven't completed a full wear-time test on {self.product_name} yet so I don't want "
            f"to guess at exact hours, though my initial impression on skin is a lovely {self.scent_family.lower()} profile."
        )


DEFAULT_FRAGRANCE_CATALOG: Tuple[FragranceRecord, ...] = (
    FragranceRecord(
        sku="EMP-VELVET-OUD-50",
        product_name="Empyrean Velvet Oud",
        brand="Empyrean",
        variant="Eau de Parfum",
        size_ml=50,
        concentration="Eau de Parfum",
        top_notes=("bergamot", "pink pepper", "saffron"),
        heart_notes=("Turkish rose", "velvet oud", "geranium"),
        base_notes=("ambergris accord", "Bourbon vanilla", "sandalwood"),
        scent_family="Warm Floral Amber Oud",
        vibe_summary="a smooth, plush rose-oud with a creamy vanilla-amber dry-down",
        wear_time_measured=True,
        wear_time_hours=(8, 10),
        sillage_profile="moderate-to-enveloping soft trail",
        public_price_gbp=145.0,
        canonical_store="Empyrean",
        raw_store_label="Experian",  # Preserved OCR quirk from receipt scan, verified by owner as Empyrean
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="NONE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-001",
        aliases=("velvet oud", "empyrean oud", "empyrean velvet"),
    ),
    FragranceRecord(
        sku="EMP-SILK-VANILLA-100",
        product_name="Empyrean Silk Vanilla",
        brand="Empyrean",
        variant="Extrait de Parfum",
        size_ml=100,
        concentration="Extrait de Parfum",
        top_notes=("cardamom", "pear blossom"),
        heart_notes=("Madagascan vanilla orchid", "cashmere wood"),
        base_notes=("tonka bean", "white musk", "benzoin"),
        scent_family="Creamy Gourmand Woods",
        vibe_summary="an airy, spun-sugar vanilla wrapped in soft cashmere woods",
        wear_time_measured=False,
        wear_time_hours=None,
        sillage_profile=None,
        public_price_gbp=165.0,
        canonical_store="Empyrean",
        raw_store_label="Empyrean",
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="AFFILIATE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-002",
        aliases=("silk vanilla", "empyrean vanilla"),
    ),
    FragranceRecord(
        sku="EMP-AMBER-NOIR-50",
        product_name="Empyrean Amber Noir",
        brand="Empyrean",
        variant="Eau de Parfum",
        size_ml=50,
        concentration="Eau de Parfum",
        top_notes=("black fig", "elemi"),
        heart_notes=("iris butter", "incense"),
        base_notes=("labdanum", "smoked cedar", "dark amber"),
        scent_family="Resinous Woody Amber",
        vibe_summary="a moody, velvety fig and iris resting on warm resinous amber",
        wear_time_measured=False,
        wear_time_hours=None,
        sillage_profile=None,
        public_price_gbp=140.0,
        canonical_store=None,
        raw_store_label="Experian",  # Unverified OCR label: must NOT be cited as Experian!
        store_verified=False,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="NONE",
        owner_confirmed=False,
        evidence_id="EVD-PUR-2026-003",
        aliases=("amber noir", "empyrean amber"),
    ),
    FragranceRecord(
        sku="PDM-DELINA-EX-75",
        product_name="Parfums de Marly Delina Exclusif",
        brand="Parfums de Marly",
        variant="Parfum",
        size_ml=75,
        concentration="Parfum",
        top_notes=("lychee", "pear", "bergamot"),
        heart_notes=("Turkish rose", "incense", "agarwood"),
        base_notes=("vanilla", "amber", "vetiver"),
        scent_family="Fruity Floral Oriental",
        vibe_summary="a opulent, creamy lychee-rose with a velvety vanilla base",
        wear_time_measured=True,
        wear_time_hours=(9, 11),
        sillage_profile="radiant soft-luxury projection",
        public_price_gbp=255.0,
        canonical_store="Selfridges",
        raw_store_label="Selfridges & Co",
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="NONE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-004",
        aliases=("delina exclusif", "delina", "pdm delina"),
    ),
    FragranceRecord(
        sku="MFK-GFS-70",
        product_name="Maison Francis Kurkdjian Gentle Fluidity Gold",
        brand="Maison Francis Kurkdjian",
        variant="Eau de Parfum",
        size_ml=70,
        concentration="Eau de Parfum",
        top_notes=("juniper berries", "nutmeg"),
        heart_notes=("coriander seed", "hedione"),
        base_notes=("vanilla accord", "amber woods", "musk"),
        scent_family="Floral Musk Vanilla",
        vibe_summary="an effortlessly polished, luminous vanilla-musk cloud",
        wear_time_measured=True,
        wear_time_hours=(7, 9),
        sillage_profile="refined, polite aura",
        public_price_gbp=195.0,
        canonical_store="Harrods",
        raw_store_label="Harrods Beauty",
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="AFFILIATE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-005",
        aliases=("gentle fluidity gold", "mfk gentle fluidity", "gfg"),
    ),
    FragranceRecord(
        sku="BYR-BAL-50",
        product_name="Byredo Bal d'Afrique",
        brand="Byredo",
        variant="Eau de Parfum",
        size_ml=50,
        concentration="Eau de Parfum",
        top_notes=("bergamot", "lemon", "neroli", "African marigold"),
        heart_notes=("violet", "jasmine petals", "cyclamen"),
        base_notes=("black amber", "musk", "vetiver", "Moroccan cedarwood"),
        scent_family="Woody Floral Vetiver",
        vibe_summary="a sunlit, sparkling citrus-vetiver with clean creamy woods",
        wear_time_measured=True,
        wear_time_hours=(4, 6),
        sillage_profile="intimate skin-scent trail",
        public_price_gbp=140.0,
        canonical_store="Space NK",
        raw_store_label="Space NK",
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="NONE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-006",
        aliases=("bal d'afrique", "bal dafrique", "byredo bal"),
    ),
    FragranceRecord(
        sku="DIP-ORPHEON-75",
        product_name="Diptyque Orphéon",
        brand="Diptyque",
        variant="Eau de Parfum",
        size_ml=75,
        concentration="Eau de Parfum",
        top_notes=("juniper berry",),
        heart_notes=("jasmine", "powdery iris"),
        base_notes=("tonka bean", "cedarwood"),
        scent_family="Woody Chypre Floral",
        vibe_summary="a chic, powdery juniper-and-tonka scent that feels like a silk blazer",
        wear_time_measured=False,
        wear_time_hours=None,
        sillage_profile=None,
        public_price_gbp=160.0,
        canonical_store="Diptyque Boutique",
        raw_store_label="Diptyque London",
        store_verified=True,
        acquisition_source="SELF_PURCHASED",
        commercial_relationship="NONE",
        owner_confirmed=True,
        evidence_id="EVD-PUR-2026-007",
        aliases=("orpheon", "orphéon", "diptyque orpheon"),
    ),
    FragranceRecord(
        sku="KAY-YUM-PISTACHIO-50",
        product_name="Kayali Yum Pistachio Gelato 33",
        brand="Kayali",
        variant="Eau de Parfum Intense",
        size_ml=50,
        concentration="Eau de Parfum Intense",
        top_notes=("pistachio", "bergamot", "hazelnut", "cardamom"),
        heart_notes=("white peach", "jasmine", "raspberry", "geranium"),
        base_notes=("whipped cream", "marshmallow", "cotton candy", "tonka bean", "sandalwood"),
        scent_family="Fluffy Nutty Gourmand",
        vibe_summary="a playful, airy pistachio and marshmallow treat with a cleanfresh opening",
        wear_time_measured=True,
        wear_time_hours=(6, 7),
        sillage_profile="cosy medium bubble",
        public_price_gbp=83.0,
        canonical_store="Sephora UK",
        raw_store_label="Sephora UK",
        store_verified=True,
        acquisition_source="PR_GIFTED",
        commercial_relationship="GIFTED_INCENTIVE",
        owner_confirmed=True,
        evidence_id="EVD-PR-2026-008",
        aliases=("yum pistachio", "pistachio gelato", "kayali pistachio"),
    ),
    FragranceRecord(
        sku="JO-SCARLET-POPPY-50",
        product_name="Jo Malone Scarlet Poppy",
        brand="Jo Malone London",
        variant="Cologne Intense",
        size_ml=50,
        concentration="Cologne Intense",
        top_notes=("ambrette",),
        heart_notes=("scarlet poppy", "iris", "fig"),
        base_notes=("tonka bean", "heliotrope", "barley"),
        scent_family="Powdery Floral Gourmand",
        vibe_summary="a comforting, velvety iris and barley scent with soft almond-like warmth",
        wear_time_measured=True,
        wear_time_hours=(6, 8),
        sillage_profile="soft, hugging aura",
        public_price_gbp=112.0,
        canonical_store="Jo Malone Boutique",
        raw_store_label="Jo Malone London",
        store_verified=True,
        acquisition_source="PAID_COLLAB" if "PAID_COLLAB" in VALID_ACQUISITION_SOURCES else "PR_GIFTED",
        commercial_relationship="PAID_COLLAB",
        owner_confirmed=True,
        evidence_id="EVD-COL-2026-009",
        aliases=("scarlet poppy", "jo malone poppy"),
    ),
)


class FragranceKnowledgeBase:
    """
    Searchable, deterministic knowledge base of verified fragrances for @annreveals.
    Provides exact SKU lookup and confidence-scored fuzzy matching (FR-020).
    """

    def __init__(self, records: Optional[Tuple[FragranceRecord, ...]] = None) -> None:
        self._records: Dict[str, FragranceRecord] = {}
        for rec in records if records is not None else DEFAULT_FRAGRANCE_CATALOG:
            self._records[rec.sku] = rec

    def get_by_sku(self, sku: str) -> Optional[FragranceRecord]:
        return self._records.get(sku)

    def list_all(self) -> List[FragranceRecord]:
        return list(self._records.values())

    def add_or_update(self, record: FragranceRecord) -> None:
        self._records[record.sku] = record

    def match_from_text(
        self,
        text: str,
        explicit_sku: Optional[str] = None,
    ) -> Tuple[Optional[FragranceRecord], float]:
        """
        Match a fragrance record from an explicit SKU or free-text comment/caption.
        Returns (FragranceRecord, confidence_score_0_to_1).
        """
        if explicit_sku and explicit_sku in self._records:
            return self._records[explicit_sku], 1.0

        cleaned = re.sub(r"[^a-z0-9\s']", " ", (text or "").lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None, 0.0

        best_record: Optional[FragranceRecord] = None
        best_score: float = 0.0

        for rec in self._records.values():
            prod_lower = rec.product_name.lower()
            if prod_lower in cleaned:
                return rec, 0.98

            for alias in rec.aliases:
                alias_lower = alias.lower()
                if alias_lower in cleaned:
                    score = 0.94 if len(alias_lower.split()) >= 2 else 0.86
                    if score > best_score:
                        best_score = score
                        best_record = rec

            # Token overlap + sequence similarity
            candidates = [prod_lower] + [a.lower() for a in rec.aliases]
            for cand in candidates:
                ratio = difflib.SequenceMatcher(None, cand, cleaned).ratio()
                cand_tokens = set(cand.split())
                text_tokens = set(cleaned.split())
                overlap = (
                    len(cand_tokens & text_tokens) / float(len(cand_tokens))
                    if cand_tokens
                    else 0.0
                )
                combined = max(ratio * 0.75, overlap * 0.88)
                if combined > best_score:
                    best_score = combined
                    best_record = rec

        if best_score < 0.55:
            return None, round(best_score, 3)
        return best_record, round(best_score, 3)
