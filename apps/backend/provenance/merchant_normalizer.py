"""
Raw-vs-Canonical Merchant Normalizer for the Verified Purchases Vault.

Implements FR-019 & FR-051:
- Preserves `merchant_label_raw` ('Experian', 'Empyrean', 'Empyrean Parfums', 'Selfridges', 'Harrods', etc.)
  separately from `normalized_name` and `normalized_domain`.
- NEVER auto-conflates 'Experian' with `experian.com` (credit reporting bureau)
  or normalizes 'Experian' -> 'Empyrean' without explicit `owner_verified=True`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class NormalizedMerchant:
    """Represents both the raw OCR/user merchant label and its canonical resolution."""

    merchant_label_raw: str
    normalized_name: str
    normalized_domain: Optional[str]
    category: str
    owner_verified: bool
    is_ambiguous_experian: bool = False
    requires_owner_confirmation: bool = False
    warnings: List[str] = field(default_factory=list)


class MerchantNormalizer:
    """
    Normalizes perfume retailer names while strictly enforcing the
    'Experian' vs 'Empyrean' disambiguation rule.
    """

    # Known canonical fragrance retailers and luxury department stores
    _CANONICAL_MERCHANTS: Dict[str, Tuple[str, str, str]] = {
        "empyrean": ("Empyrean Parfums", "empyreanparfums.com", "NICHE_PERFUME_HOUSE"),
        "empyrean parfums": ("Empyrean Parfums", "empyreanparfums.com", "NICHE_PERFUME_HOUSE"),
        "empyrean fragrances": ("Empyrean Parfums", "empyreanparfums.com", "NICHE_PERFUME_HOUSE"),
        "empyrean london": ("Empyrean Parfums", "empyreanparfums.com", "NICHE_PERFUME_HOUSE"),
        "selfridges": ("Selfridges", "selfridges.com", "LUXURY_DEPARTMENT_STORE"),
        "selfridges & co": ("Selfridges", "selfridges.com", "LUXURY_DEPARTMENT_STORE"),
        "selfridges london": ("Selfridges", "selfridges.com", "LUXURY_DEPARTMENT_STORE"),
        "harrods": ("Harrods", "harrods.com", "LUXURY_DEPARTMENT_STORE"),
        "harrods knightsbridge": ("Harrods", "harrods.com", "LUXURY_DEPARTMENT_STORE"),
        "liberty": ("Liberty London", "libertylondon.com", "LUXURY_DEPARTMENT_STORE"),
        "liberty london": ("Liberty London", "libertylondon.com", "LUXURY_DEPARTMENT_STORE"),
        "john lewis": ("John Lewis & Partners", "johnlewis.com", "DEPARTMENT_STORE"),
        "john lewis & partners": ("John Lewis & Partners", "johnlewis.com", "DEPARTMENT_STORE"),
        "harvey nichols": ("Harvey Nichols", "harveynichols.com", "LUXURY_DEPARTMENT_STORE"),
        "space nk": ("Space NK", "spacenk.com", "BEAUTY_RETAILER"),
        "cult beauty": ("Cult Beauty", "cultbeauty.co.uk", "BEAUTY_RETAILER"),
        "les senteurs": ("Les Senteurs", "lessenteurs.com", "NICHE_PERFUMERY"),
        "bloom perfumery": ("Bloom Perfumery London", "bloomperfumery.co.uk", "NICHE_PERFUMERY"),
        "jovoy": ("Jovoy Mayfair", "jovoyparis.uk", "NICHE_PERFUMERY"),
        "fragrance du bois": ("Fragrance Du Bois", "fragrancedubois.com", "NICHE_PERFUME_HOUSE"),
        "parfums de marly": ("Parfums de Marly", "parfums-de-marly.com", "NICHE_PERFUME_HOUSE"),
        "byredo": ("Byredo", "byredo.com", "NICHE_PERFUME_HOUSE"),
        "diptyque": ("Diptyque", "diptyqueparis.com", "NICHE_PERFUME_HOUSE"),
        "le labo": ("Le Labo", "lelabofragrances.com", "NICHE_PERFUME_HOUSE"),
        "penhaligon's": ("Penhaligon's", "penhaligons.com", "NICHE_PERFUME_HOUSE"),
        "penhaligons": ("Penhaligon's", "penhaligons.com", "NICHE_PERFUME_HOUSE"),
        "jo malone": ("Jo Malone London", "jomalone.co.uk", "PERFUME_HOUSE"),
        "jo malone london": ("Jo Malone London", "jomalone.co.uk", "PERFUME_HOUSE"),
        "boots": ("Boots UK", "boots.com", "PHARMACY_BEAUTY_RETAILER"),
        "the perfume shop": ("The Perfume Shop", "theperfumeshop.com", "PERFUME_RETAILER"),
        "notino": ("Notino UK", "notino.co.uk", "PERFUME_RETAILER"),
        "allbeauty": ("allbeauty", "allbeauty.com", "PERFUME_RETAILER"),
    }

    def normalize(
        self,
        merchant_label_raw: str,
        owner_verified: bool = False,
        confirmed_canonical_key: Optional[str] = None,
    ) -> NormalizedMerchant:
        """
        Normalize a raw merchant label while preserving `merchant_label_raw`.

        Special Rule (FR-019 / FR-051):
        If `merchant_label_raw` references 'Experian' (or 'experian.com' / 'experian.co.uk'):
        - NEVER assign `experian.com` as a perfume store domain.
        - If `owner_verified=False`, return `normalized_name="UNVERIFIED_MERCHANT"`,
          `normalized_domain=None`, `is_ambiguous_experian=True`, `requires_owner_confirmation=True`.
        - Only when `owner_verified=True` (owner explicitly confirms the receipt is from Empyrean Parfums)
          does `normalized_name` resolve to `'Empyrean Parfums'` and `normalized_domain` to `'empyreanparfums.com'`,
          while permanently retaining `merchant_label_raw='Experian'`.
        """
        raw_preserved = (merchant_label_raw or "").strip()
        if not raw_preserved:
            return NormalizedMerchant(
                merchant_label_raw="",
                normalized_name="UNKNOWN_MERCHANT",
                normalized_domain=None,
                category="UNKNOWN",
                owner_verified=False,
                is_ambiguous_experian=False,
                requires_owner_confirmation=True,
                warnings=["MISSING_MERCHANT_LABEL: No merchant name was found on the receipt."],
            )

        cleaned_lower = raw_preserved.lower()

        # Explicit guard against 'Experian' credit bureau conflation
        if "experian" in cleaned_lower:
            if not owner_verified:
                return NormalizedMerchant(
                    merchant_label_raw=raw_preserved,
                    normalized_name="UNVERIFIED_MERCHANT",
                    normalized_domain=None,
                    category="AMBIGUOUS_CREDIT_BUREAU_VS_PERFUMERY",
                    owner_verified=False,
                    is_ambiguous_experian=True,
                    requires_owner_confirmation=True,
                    warnings=[
                        "AMBIGUOUS_MERCHANT_EXPERIAN_EMPYREAN: Raw label "
                        f"'{raw_preserved}' preserved. Never conflated with experian.com "
                        "(credit reporting bureau) and never auto-normalized to 'Empyrean Parfums' "
                        "without explicit owner_verified=True."
                    ],
                )
            # Owner explicitly verified that "Experian" was an OCR/voice typo for Empyrean Parfums
            target_key = (confirmed_canonical_key or "empyrean parfums").lower()
            canon_name, canon_domain, canon_cat = self._CANONICAL_MERCHANTS.get(
                target_key,
                ("Empyrean Parfums", "empyreanparfums.com", "NICHE_PERFUME_HOUSE"),
            )
            return NormalizedMerchant(
                merchant_label_raw=raw_preserved,
                normalized_name=canon_name,
                normalized_domain=canon_domain,
                category=canon_cat,
                owner_verified=True,
                is_ambiguous_experian=True,
                requires_owner_confirmation=False,
                warnings=[
                    f"OWNER_VERIFIED_ALIAS: Raw label '{raw_preserved}' preserved in audit trail; "
                    f"confirmed by owner as '{canon_name}' ({canon_domain})."
                ],
            )

        # Exact or substring match against known perfume merchants
        if cleaned_lower in self._CANONICAL_MERCHANTS:
            canon_name, canon_domain, canon_cat = self._CANONICAL_MERCHANTS[cleaned_lower]
            return NormalizedMerchant(
                merchant_label_raw=raw_preserved,
                normalized_name=canon_name,
                normalized_domain=canon_domain,
                category=canon_cat,
                owner_verified=owner_verified,
                is_ambiguous_experian=False,
                requires_owner_confirmation=False,
                warnings=[],
            )

        for key, (canon_name, canon_domain, canon_cat) in self._CANONICAL_MERCHANTS.items():
            if key in cleaned_lower:
                return NormalizedMerchant(
                    merchant_label_raw=raw_preserved,
                    normalized_name=canon_name,
                    normalized_domain=canon_domain,
                    category=canon_cat,
                    owner_verified=owner_verified,
                    is_ambiguous_experian=False,
                    requires_owner_confirmation=False,
                    warnings=[],
                )

        # Unrecognized retailer
        if owner_verified:
            return NormalizedMerchant(
                merchant_label_raw=raw_preserved,
                normalized_name=raw_preserved,
                normalized_domain=None,
                category="OWNER_CONFIRMED_CUSTOM_RETAILER",
                owner_verified=True,
                is_ambiguous_experian=False,
                requires_owner_confirmation=False,
                warnings=[],
            )

        return NormalizedMerchant(
            merchant_label_raw=raw_preserved,
            normalized_name="UNVERIFIED_MERCHANT",
            normalized_domain=None,
            category="UNRECOGNIZED_RETAILER",
            owner_verified=False,
            is_ambiguous_experian=False,
            requires_owner_confirmation=True,
            warnings=[
                f"UNRECOGNIZED_MERCHANT: '{raw_preserved}' is not in the canonical perfume retailer "
                "registry. Owner confirmation required."
            ],
        )
