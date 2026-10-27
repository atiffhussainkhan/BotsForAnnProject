"""
Comprehensive Unittest Suite for Agent Delta (Purchase Evidence, UK Advertising Compliance,
Dual-Platform Preflight, and Appeals Specialist).

Tests:
1. PII, Payment Card (PAN/Luhn/Last-4), IBAN, Sort Code, Address, Postcode, Email, Phone, and Barcode Redaction.
2. Raw-vs-Canonical Merchant Normalizer ('Experian' vs 'Empyrean' disambiguation rule — never experian.com).
3. All 30 Fictional Receipt Edge Cases (correct, wrong size, refunded, PR free, discounted, affiliate,
   no proof, duplicated order, mismatched email, unknown/Experian merchant).
4. All 10 Mandatory Dual-Platform Compliance Scenarios (Rules G1–G5, UK ASA upfront 'Ad |', Meta & TikTok toggles).
5. Dual-Platform Content Studio (Sample Case A Instagram & Sample Case B TikTok + anti-spam ownership comment rotation).
6. FR-058 Retroactive Receipt Contradiction Guard (never silently alter already-published claims).
7. FR-029–FR-033 & Rule G6 Violation Intake (all 9 categories), Automatic Post Automation Freeze,
   Root-Cause Analysis without false certainty, and Redacted Appeal Packet Builder.
"""

from __future__ import annotations

import unittest

from apps.backend.appeals import (
    AppealLifecycleStatus,
    AppealPacketBuilder,
    AppealsTracker,
    ViolationCategory,
)
from apps.backend.compliance import (
    DEFAULT_FIVE_HASHTAGS,
    CommercialRelationship,
    ContentStudioRequest,
    DisclosureEngine,
    DualPlatformContentStudio,
    PlatformType,
    PreflightChecker,
    PreflightInput,
    ProvenanceStatus,
    RiskGrade,
)
from apps.backend.provenance import (
    MerchantNormalizer,
    PerfumeItem,
    ReceiptRedactor,
    VaultConfidenceStatus,
    VerifiedPurchasesVault,
)


class TestAgentDeltaProvenanceAndCompliance(unittest.TestCase):
    """End-to-end verification of Agent Delta deliverables."""

    def setUp(self) -> None:
        self.redactor = ReceiptRedactor()
        self.normalizer = MerchantNormalizer()
        self.vault = VerifiedPurchasesVault(
            owner_emails=["ann@annreveals.co.uk", "ann.reveals@gmail.com"]
        )
        self.engine = DisclosureEngine()
        self.preflight = PreflightChecker(
            disclosure_engine=self.engine,
            redactor=self.redactor,
        )
        self.studio = DualPlatformContentStudio(
            disclosure_engine=self.engine,
            preflight_checker=self.preflight,
        )
        self.appeals_tracker = AppealsTracker()
        self.packet_builder = AppealPacketBuilder(redactor=self.redactor)

        # Register core catalog items for testing
        self.vault.register_item(
            PerfumeItem(
                sku="EMP-IRIS-100",
                product_name="Celestial Iris",
                brand="Empyrean Parfums",
                variant="Extrait",
                size_ml=100,
                concentration="Extrait de Parfum",
                store="Empyrean Parfums",
                purchase_date="2026-10-15",
                private_price=195.00,
            )
        )
        self.vault.register_item(
            PerfumeItem(
                sku="PDM-DELINA-75",
                product_name="Delina",
                brand="Parfums de Marly",
                variant="Original",
                size_ml=75,
                concentration="EDP",
                store="Selfridges",
                purchase_date="2026-10-16",
                private_price=255.00,
            )
        )
        self.vault.register_item(
            PerfumeItem(
                sku="MFK-BR540-70",
                product_name="Baccarat Rouge 540",
                brand="Maison Francis Kurkdjian",
                variant="",
                size_ml=70,
                concentration="EDP",
                store="Harrods",
                purchase_date="2026-10-17",
                private_price=245.00,
            )
        )
        self.vault.register_item(
            PerfumeItem(
                sku="BYR-MOJAVE-100",
                product_name="Mojave Ghost",
                brand="Byredo",
                variant="",
                size_ml=100,
                concentration="EDP",
                store="Liberty London",
                purchase_date="2026-10-18",
                private_price=210.00,
            )
        )
        self.vault.register_item(
            PerfumeItem(
                sku="DIP-ORPHEON-75",
                product_name="Orpheon",
                brand="Diptyque",
                variant="",
                size_ml=75,
                concentration="EDP",
                store="Les Senteurs",
                purchase_date="2026-10-19",
                private_price=160.00,
            )
        )
        self.vault.register_item(
            PerfumeItem(
                sku="JML-WOODSAGE-100",
                product_name="Wood Sage & Sea Salt",
                brand="Jo Malone London",
                variant="",
                size_ml=100,
                concentration="EDC",
                store="Jo Malone London",
                purchase_date="2026-10-20",
                private_price=118.00,
            )
        )

    def test_01_pii_and_payment_redactor(self) -> None:
        """Verify deterministic scrubbing of PANs, Last-4, IBAN, Sort Code, Address, Postcode, Email, Phone, and Barcode."""
        raw_receipt = (
            "Empyrean Parfums London\n"
            "Order ID: ORD-2026-998811\n"
            "Customer Email: ann@annreveals.co.uk\n"
            "Contact Phone: +44 7700 900077\n"
            "Billing Address: Flat 4B, 14 Kensington High Street, London, SW1X 7XL\n"
            "Payment Card: 4532 0151 1283 0366\n"
            "Backup Card: Visa ending in 4421\n"
            "Bank Refund IBAN: GB29 NWBK 6016 1331 9268 19\n"
            "Sort Code: 20-45-19  Account Number: 12345678\n"
            "QR_PAYLOAD: https://empyreanparfums.com/verify-receipt/token-secret-991\n"
            "BARCODE: ||| |||| || |||||\n"
            "Item: Celestial Iris Extrait de Parfum 100ml - £195.00\n"
        )
        res = self.redactor.redact(
            raw_text=raw_receipt,
            owner_emails=["ann@annreveals.co.uk"],
        )
        self.assertTrue(res.purchaser_email_matched_owner)
        self.assertNotIn("4532 0151 1283 0366", res.redacted_text)
        self.assertNotIn("ending in 4421", res.redacted_text)
        self.assertNotIn("GB29 NWBK", res.redacted_text)
        self.assertNotIn("20-45-19", res.redacted_text)
        self.assertNotIn("12345678", res.redacted_text)
        self.assertNotIn("ann@annreveals.co.uk", res.redacted_text)
        self.assertNotIn("7700 900077", res.redacted_text)
        self.assertNotIn("14 Kensington High Street", res.redacted_text)
        self.assertNotIn("SW1X 7XL", res.redacted_text)
        self.assertNotIn("ORD-2026-998811", res.redacted_text)
        self.assertNotIn("verify-receipt/token-secret-991", res.redacted_text)
        self.assertFalse(self.redactor.contains_unredacted_pii(res.redacted_text))
        self.assertEqual(len(res.raw_sha256), 64)

    def test_02_experian_vs_empyrean_merchant_normalizer_guard(self) -> None:
        """
        Verify FR-019 / FR-051:
        - 'Experian' is NEVER mapped to experian.com (credit bureau).
        - Without owner_verified=True, 'Experian' remains UNVERIFIED_MERCHANT with requires_owner_confirmation=True.
        - With owner_verified=True, 'Experian' resolves to 'Empyrean Parfums' ('empyreanparfums.com') while
          preserving merchant_label_raw='Experian'.
        """
        unverified = self.normalizer.normalize("Experian", owner_verified=False)
        self.assertEqual(unverified.merchant_label_raw, "Experian")
        self.assertEqual(unverified.normalized_name, "UNVERIFIED_MERCHANT")
        self.assertIsNone(unverified.normalized_domain)
        self.assertTrue(unverified.is_ambiguous_experian)
        self.assertTrue(unverified.requires_owner_confirmation)
        self.assertTrue(any("experian.com" in w for w in unverified.warnings))

        verified = self.normalizer.normalize("Experian", owner_verified=True)
        self.assertEqual(verified.merchant_label_raw, "Experian")
        self.assertEqual(verified.normalized_name, "Empyrean Parfums")
        self.assertEqual(verified.normalized_domain, "empyreanparfums.com")
        self.assertNotEqual(verified.normalized_domain, "experian.com")
        self.assertTrue(verified.is_ambiguous_experian)
        self.assertFalse(verified.requires_owner_confirmation)

    def test_03_thirty_fictional_receipt_edge_cases(self) -> None:
        """
        Test all 30 mandatory receipt edge cases across:
        - Correct receipts (RC-01 to RC-06)
        - Wrong bottle size (RC-07 to RC-09)
        - Refunded / cancelled / chargeback (RC-10 to RC-12)
        - Free PR / complimentary / 2ml sample vial (RC-13 to RC-15)
        - Discounted / 100% voucher (RC-16 to RC-18)
        - Affiliate metadata on receipt (RC-19 to RC-21)
        - No proof / blank OCR (RC-22 to RC-23)
        - Duplicated order references (RC-24 to RC-25)
        - Mismatched purchaser emails (RC-26 to RC-27)
        - Unknown / Experian unconfirmed merchants (RC-28 to RC-30)
        """
        results = {}

        # RC-01: Correct Empyrean Parfums 100ml Extrait
        results["RC-01"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-99001\nBuyer: ann@annreveals.co.uk\nCelestial Iris Extrait 100ml £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            raw_order_ref="ORD-EMP-99001",
        )
        self.assertEqual(results["RC-01"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-02: Correct Selfridges Delina 75ml EDP with PAN & postcode redacted
        results["RC-02"] = self.vault.ingest_receipt_for_item(
            sku="PDM-DELINA-75",
            raw_text="Invoice ID: INV-SLF-77412\nann@annreveals.co.uk\n4532015112830366\nSW1X 7XL\nDelina 75ml EDP £255.00",
            merchant_label_raw="Selfridges & Co",
            extracted_brand="Parfums de Marly",
            extracted_product_name="Delina",
            extracted_variant="Original",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=255.00,
            net_paid=255.00,
            raw_order_ref="INV-SLF-77412",
        )
        self.assertEqual(results["RC-02"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-03: Correct Harrods BR540 70ml EDP
        results["RC-03"] = self.vault.ingest_receipt_for_item(
            sku="MFK-BR540-70",
            raw_text="Order Ref: HRD-1003\nVisa ending in 4421\nBaccarat Rouge 540 70ml EDP £245.00",
            merchant_label_raw="Harrods Knightsbridge",
            extracted_brand="Maison Francis Kurkdjian",
            extracted_product_name="Baccarat Rouge 540",
            extracted_concentration="EDP",
            extracted_size_ml=70,
            subtotal_price=245.00,
            net_paid=245.00,
            raw_order_ref="HRD-1003",
        )
        self.assertEqual(results["RC-03"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-04: Correct Liberty London Byredo Mojave Ghost 100ml EDP
        results["RC-04"] = self.vault.ingest_receipt_for_item(
            sku="BYR-MOJAVE-100",
            raw_text="Order Ref: LIB-1004\nSort Code: 12-34-56\nByredo Mojave Ghost 100ml EDP £210.00",
            merchant_label_raw="Liberty London",
            extracted_brand="Byredo",
            extracted_product_name="Mojave Ghost",
            extracted_concentration="EDP",
            extracted_size_ml=100,
            subtotal_price=210.00,
            net_paid=210.00,
            raw_order_ref="LIB-1004",
        )
        self.assertEqual(results["RC-04"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-05: Correct Les Senteurs Diptyque Orpheon 75ml EDP
        results["RC-05"] = self.vault.ingest_receipt_for_item(
            sku="DIP-ORPHEON-75",
            raw_text="Order Ref: LSN-1005\nBARCODE: |||| ||| ||||\nDiptyque Orpheon 75ml EDP £160.00",
            merchant_label_raw="Les Senteurs",
            extracted_brand="Diptyque",
            extracted_product_name="Orpheon",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=160.00,
            net_paid=160.00,
            raw_order_ref="LSN-1005",
        )
        self.assertEqual(results["RC-05"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-06: Correct Owner-Verified 'Experian' -> 'Empyrean Parfums'
        results["RC-06"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1006\nExperian Parfums Celestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Experian",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            owner_verified_merchant=True,
            raw_order_ref="ORD-EMP-1006",
        )
        self.assertEqual(results["RC-06"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-07: Wrong Size (50ml receipt vs 100ml catalog item)
        results["RC-07"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1007\nCelestial Iris Extrait 50ml £135.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=50,
            subtotal_price=135.00,
            net_paid=135.00,
            raw_order_ref="ORD-EMP-1007",
        )
        self.assertEqual(results["RC-07"].status, VaultConfidenceStatus.UNVERIFIED)
        self.assertTrue(any("SIZE_MISMATCH" in d for d in results["RC-07"].discrepancies))

        # RC-08: Wrong Size (10ml travel spray vs 75ml bottle)
        results["RC-08"] = self.vault.ingest_receipt_for_item(
            sku="PDM-DELINA-75",
            raw_text="Order Ref: SLF-1008\nParfums de Marly Delina 10ml EDP £42.00",
            merchant_label_raw="Selfridges",
            extracted_brand="Parfums de Marly",
            extracted_product_name="Delina",
            extracted_variant="Original",
            extracted_concentration="EDP",
            extracted_size_ml=10,
            subtotal_price=42.00,
            net_paid=42.00,
            raw_order_ref="SLF-1008",
        )
        self.assertEqual(results["RC-08"].status, VaultConfidenceStatus.UNVERIFIED)
        self.assertTrue(any("SIZE_MISMATCH" in d for d in results["RC-08"].discrepancies))

        # RC-09: Wrong Size (30ml Jo Malone vs 100ml catalog bottle)
        results["RC-09"] = self.vault.ingest_receipt_for_item(
            sku="JML-WOODSAGE-100",
            raw_text="Order Ref: JML-1009\nJo Malone Wood Sage & Sea Salt 30ml EDC £56.00",
            merchant_label_raw="Jo Malone London",
            extracted_brand="Jo Malone London",
            extracted_product_name="Wood Sage & Sea Salt",
            extracted_concentration="EDC",
            extracted_size_ml=30,
            subtotal_price=56.00,
            net_paid=56.00,
            raw_order_ref="JML-1009",
        )
        self.assertEqual(results["RC-09"].status, VaultConfidenceStatus.UNVERIFIED)

        # RC-10: Refunded Order (Full Refund)
        results["RC-10"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1010\nCelestial Iris 100ml Extrait — STATUS: FULL REFUND £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=0.0,
            raw_order_ref="ORD-EMP-1010",
        )
        self.assertEqual(results["RC-10"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-11: Cancelled Order before dispatch
        results["RC-11"] = self.vault.ingest_receipt_for_item(
            sku="PDM-DELINA-75",
            raw_text="Order Ref: SLF-1011\nDelina 75ml EDP — ORDER CANCELLED",
            merchant_label_raw="Selfridges",
            extracted_brand="Parfums de Marly",
            extracted_product_name="Delina",
            extracted_variant="Original",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=255.00,
            net_paid=0.0,
            raw_order_ref="SLF-1011",
        )
        self.assertEqual(results["RC-11"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-12: Chargeback / Payment Reversed
        results["RC-12"] = self.vault.ingest_receipt_for_item(
            sku="MFK-BR540-70",
            raw_text="Order Ref: HRD-1012\nBaccarat Rouge 540 70ml EDP — PAYMENT REVERSED / CHARGEBACK",
            merchant_label_raw="Harrods",
            extracted_brand="Maison Francis Kurkdjian",
            extracted_product_name="Baccarat Rouge 540",
            extracted_concentration="EDP",
            extracted_size_ml=70,
            subtotal_price=245.00,
            net_paid=0.0,
            raw_order_ref="HRD-1012",
        )
        self.assertEqual(results["RC-12"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-13: PR Free Sample Packing Slip (£0.00) claimed as SELF_PURCHASED
        results["RC-13"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: PR-EMP-1013\nPR SAMPLE - NOT FOR RESALE\nCelestial Iris 100ml £0.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=0.0,
            net_paid=0.0,
            raw_order_ref="PR-EMP-1013",
            claimed_self_purchased=True,
        )
        self.assertEqual(results["RC-13"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-14: Influencer Seeding Press Gift (£0.00) claimed as SELF_PURCHASED
        results["RC-14"] = self.vault.ingest_receipt_for_item(
            sku="BYR-MOJAVE-100",
            raw_text="Order Ref: PR-BYR-1014\nINFLUENCER SEEDING PRESS GIFT — Complimentary £0.00",
            merchant_label_raw="Byredo",
            extracted_brand="Byredo",
            extracted_product_name="Mojave Ghost",
            extracted_concentration="EDP",
            extracted_size_ml=100,
            subtotal_price=0.0,
            net_paid=0.0,
            raw_order_ref="PR-BYR-1014",
            claimed_self_purchased=True,
        )
        self.assertEqual(results["RC-14"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-15: Free 2ml GWP Sample Vial attached to 100ml full bottle claim
        results["RC-15"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: GWP-1015\nComplimentary 2ml discovery vial GWP sample £0.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=2,
            subtotal_price=0.0,
            net_paid=0.0,
            raw_order_ref="GWP-1015",
        )
        self.assertEqual(results["RC-15"].status, VaultConfidenceStatus.CONFLICTED)
        self.assertTrue(any("SAMPLE_VIAL_MISMATCH" in d for d in results["RC-15"].discrepancies))

        # RC-16: Discounted Self-Purchase (10% VIP10, net paid £175.50 > 0)
        results["RC-16"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1016\nPromo Code: VIP10\nCelestial Iris 100ml Extrait £175.50",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            discount_amount=19.50,
            net_paid=175.50,
            raw_order_ref="ORD-EMP-1016",
        )
        self.assertEqual(results["RC-16"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)
        self.assertTrue(any("DISCOUNT_APPLIED_ON_RECEIPT" in w for w in results["RC-16"].warnings))

        # RC-17: Discounted Self-Purchase (20% Black Friday BF20, net paid £204.00 > 0)
        results["RC-17"] = self.vault.ingest_receipt_for_item(
            sku="PDM-DELINA-75",
            raw_text="Order Ref: SLF-1017\nDiscount Code: BF20\nDelina 75ml EDP £204.00",
            merchant_label_raw="Selfridges",
            extracted_brand="Parfums de Marly",
            extracted_product_name="Delina",
            extracted_variant="Original",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=255.00,
            discount_amount=51.00,
            net_paid=204.00,
            raw_order_ref="SLF-1017",
        )
        self.assertEqual(results["RC-17"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        # RC-18: 100% Brand Voucher (£195 subtotal - £195 discount = £0.00 net paid)
        results["RC-18"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1018\nVoucher Code: PRESS100\nCelestial Iris 100ml £0.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            discount_amount=195.00,
            net_paid=0.0,
            raw_order_ref="ORD-EMP-1018",
        )
        self.assertEqual(results["RC-18"].status, VaultConfidenceStatus.UNVERIFIED)
        self.assertTrue(any("ZERO_NET_PAID_WITH_VOUCHER" in w for w in results["RC-18"].warnings))

        # RC-19: Affiliate Metadata on Receipt (LTK tracking)
        results["RC-19"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1019\nLTK tracking / affiliate commission\nCelestial Iris 100ml £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            raw_order_ref="ORD-EMP-1019",
        )
        self.assertEqual(results["RC-19"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)
        self.assertTrue(any("AFFILIATE_METADATA_ON_RECEIPT" in w for w in results["RC-19"].warnings))

        # RC-20: Affiliate Metadata on Receipt (ShopMy commission)
        results["RC-20"] = self.vault.ingest_receipt_for_item(
            sku="DIP-ORPHEON-75",
            raw_text="Order Ref: LSN-1020\nShopMy commission referral\nDiptyque Orpheon 75ml EDP £160.00",
            merchant_label_raw="Les Senteurs",
            extracted_brand="Diptyque",
            extracted_product_name="Orpheon",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=160.00,
            net_paid=160.00,
            raw_order_ref="LSN-1020",
        )
        self.assertEqual(results["RC-20"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)
        self.assertTrue(any("AFFILIATE_METADATA_ON_RECEIPT" in w for w in results["RC-20"].warnings))

        # RC-21: Affiliate Metadata on Receipt (TikTok Shop affiliate)
        results["RC-21"] = self.vault.ingest_receipt_for_item(
            sku="BYR-MOJAVE-100",
            raw_text="Order Ref: LIB-1021\nTikTok Shop affiliate order\nByredo Mojave Ghost 100ml EDP £210.00",
            merchant_label_raw="Liberty London",
            extracted_brand="Byredo",
            extracted_product_name="Mojave Ghost",
            extracted_concentration="EDP",
            extracted_size_ml=100,
            subtotal_price=210.00,
            net_paid=210.00,
            raw_order_ref="LIB-1021",
        )
        self.assertEqual(results["RC-21"].status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)
        self.assertTrue(any("AFFILIATE_METADATA_ON_RECEIPT" in w for w in results["RC-21"].warnings))

        # RC-22: No Proof Uploaded (receipt=None)
        results["RC-22"] = self.vault.evaluate_item_without_receipt("EMP-IRIS-100")
        self.assertEqual(results["RC-22"].status, VaultConfidenceStatus.UNVERIFIED)
        self.assertEqual(results["RC-22"].confidence_score, 0.0)

        # RC-23: Blank / Unreadable OCR Receipt
        results["RC-23"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="",
            merchant_label_raw="",
            extracted_brand="",
            extracted_product_name="",
            extracted_concentration="",
            extracted_size_ml=None,
            subtotal_price=0.0,
            net_paid=0.0,
        )
        self.assertEqual(results["RC-23"].status, VaultConfidenceStatus.UNVERIFIED)

        # RC-24: Duplicated Order Ref (reusing ORD-EMP-99001 from RC-01)
        results["RC-24"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-99001\nCelestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            raw_order_ref="ORD-EMP-99001",
        )
        self.assertEqual(results["RC-24"].status, VaultConfidenceStatus.CONFLICTED)
        self.assertTrue(results["RC-24"].is_duplicate_order)

        # RC-25: Duplicated Order Ref (reusing INV-SLF-77412 from RC-02)
        results["RC-25"] = self.vault.ingest_receipt_for_item(
            sku="PDM-DELINA-75",
            raw_text="Invoice ID: INV-SLF-77412\nDelina 75ml EDP £255.00",
            merchant_label_raw="Selfridges",
            extracted_brand="Parfums de Marly",
            extracted_product_name="Delina",
            extracted_variant="Original",
            extracted_concentration="EDP",
            extracted_size_ml=75,
            subtotal_price=255.00,
            net_paid=255.00,
            raw_order_ref="INV-SLF-77412",
        )
        self.assertEqual(results["RC-25"].status, VaultConfidenceStatus.CONFLICTED)
        self.assertTrue(results["RC-25"].is_duplicate_order)

        # RC-26: Mismatched Purchaser Email (stranger99@yahoo.co.uk)
        results["RC-26"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EMP-1026\nCustomer: stranger99@yahoo.co.uk\nCelestial Iris 100ml £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            raw_order_ref="ORD-EMP-1026",
        )
        self.assertEqual(results["RC-26"].status, VaultConfidenceStatus.CONFLICTED)
        self.assertTrue(any("MISMATCHED_PURCHASER_EMAIL" in d for d in results["RC-26"].discrepancies))

        # RC-27: Mismatched Purchaser Email (PR agency email seeding@pr-agency.co.uk)
        results["RC-27"] = self.vault.ingest_receipt_for_item(
            sku="MFK-BR540-70",
            raw_text="Order Ref: HRD-1027\nBuyer: seeding@pr-agency.co.uk\nBaccarat Rouge 540 70ml EDP £245.00",
            merchant_label_raw="Harrods",
            extracted_brand="Maison Francis Kurkdjian",
            extracted_product_name="Baccarat Rouge 540",
            extracted_concentration="EDP",
            extracted_size_ml=70,
            subtotal_price=245.00,
            net_paid=245.00,
            raw_order_ref="HRD-1027",
        )
        self.assertEqual(results["RC-27"].status, VaultConfidenceStatus.CONFLICTED)

        # RC-28: Unverified 'Experian' merchant (owner_verified=False)
        results["RC-28"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EXP-1028\nExperian — Celestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Experian",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            owner_verified_merchant=False,
            raw_order_ref="ORD-EXP-1028",
        )
        self.assertEqual(results["RC-28"].status, VaultConfidenceStatus.UNVERIFIED)
        self.assertTrue(any("UNCONFIRMED_MERCHANT" in d for d in results["RC-28"].discrepancies))

        # RC-29: Unverified 'Experian UK' merchant (owner_verified=False)
        results["RC-29"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-EXP-1029\nExperian UK — Celestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Experian UK",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            owner_verified_merchant=False,
            raw_order_ref="ORD-EXP-1029",
        )
        self.assertEqual(results["RC-29"].status, VaultConfidenceStatus.UNVERIFIED)

        # RC-30: Unrecognized merchant ('Mystery Bazaar Perfumes Ltd', owner_verified=False)
        results["RC-30"] = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: MYS-1030\nCelestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Mystery Bazaar Perfumes Ltd",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            owner_verified_merchant=False,
            raw_order_ref="MYS-1030",
        )
        self.assertEqual(results["RC-30"].status, VaultConfidenceStatus.UNVERIFIED)

        self.assertEqual(len(results), 30)

    def test_04_ten_mandatory_compliance_scenarios(self) -> None:
        """
        Verify all 10 mandatory compliance scenarios across Instagram and TikTok.
        """
        # Scenario 1: Instagram Pure Verified Self-Purchase (Sample Case A)
        pkg_a = self.studio.build_sample_case_a_instagram()
        self.assertEqual(pkg_a.platform, PlatformType.INSTAGRAM)
        self.assertEqual(pkg_a.preflight_report.overall_grade, RiskGrade.GREEN)
        self.assertFalse(pkg_a.preflight_report.decision.requires_upfront_uk_asa_ad_label)
        self.assertFalse(pkg_a.preflight_report.decision.native_platform_toggle_required)
        self.assertIn("Purchased with my own money. These are my personal impressions.", pkg_a.caption)
        self.assertEqual(len(pkg_a.hashtags), 5)

        # Scenario 2: TikTok Pure Verified Self-Purchase (Sample Case B)
        pkg_b = self.studio.build_sample_case_b_tiktok(with_affiliate_link=False)
        self.assertEqual(pkg_b.platform, PlatformType.TIKTOK)
        self.assertEqual(pkg_b.preflight_report.overall_grade, RiskGrade.GREEN)
        self.assertFalse(pkg_b.preflight_report.decision.native_platform_toggle_required)
        self.assertIn("Purchased with my own money", pkg_b.caption)

        # Scenario 3: Self-Purchased + Affiliate Link (Rule G1 & G2: 'not an ad' hard-blocked)
        pkg_b_aff = self.studio.build_sample_case_b_tiktok(with_affiliate_link=True)
        self.assertTrue(pkg_b_aff.caption.startswith("Ad | "))
        self.assertTrue(pkg_b_aff.preflight_report.decision.native_platform_toggle_required)
        self.assertEqual(pkg_b_aff.preflight_report.overall_grade, RiskGrade.GREEN)

        # Now test what happens if user tries to write "I bought this myself, not an ad" with an affiliate link
        bad_aff_report = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.INSTAGRAM,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
                commercial_relationships=[CommercialRelationship.AFFILIATE_LINK],
                caption_text="I bought this myself, not an ad! Link in bio to shop.",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=True,
            )
        )
        self.assertEqual(bad_aff_report.overall_grade, RiskGrade.RED)
        self.assertTrue(any("RULE_G2_VIOLATION" in b for b in bad_aff_report.blocking_issues))
        self.assertTrue(any("RULE_G3_VIOLATION" in b for b in bad_aff_report.blocking_issues))

        # Scenario 4: Self-Purchased + TikTok Shop Anchor + Non-Commercial Pop Music -> RED
        tt_shop_pop_music = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.TIKTOK,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
                commercial_relationships=[CommercialRelationship.TIKTOK_SHOP],
                caption_text="Ad | I bought this bottle myself (linked on TikTok Shop).",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=True,
                uses_non_commercial_licensed_music=True,
                has_tiktok_shop_anchor=True,
            )
        )
        self.assertEqual(tt_shop_pop_music.overall_grade, RiskGrade.RED)
        self.assertTrue(any("COMMERCIAL_MUSIC_VIOLATION" in b for b in tt_shop_pop_music.blocking_issues))

        # Scenario 5: Self-Purchased + Viewer Discount Code (PROMO_CODE) -> Requires 'Ad |' + Toggle ON
        promo_report = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.INSTAGRAM,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
                commercial_relationships=[CommercialRelationship.PROMO_CODE],
                caption_text="Ad | I bought this bottle myself (use code ANN10 for 10% off).",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=True,
            )
        )
        self.assertEqual(promo_report.overall_grade, RiskGrade.GREEN)

        # Scenario 6: Gifted PR Bottle with '#gifted' only (no upfront 'Ad') -> RED (Rule G3)
        gifted_bad = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.INSTAGRAM,
                provenance_status=ProvenanceStatus.PR_GIFTED,
                vault_confidence=VaultConfidenceStatus.UNVERIFIED,
                commercial_relationships=[CommercialRelationship.GIFTED_INCENTIVE],
                caption_text="So excited to try Celestial Iris! Thank you @empyreanparfums #gifted #pr",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=True,
            )
        )
        self.assertEqual(gifted_bad.overall_grade, RiskGrade.RED)
        self.assertTrue(any("RULE_G3_AMBIGUOUS_LABEL" in b for b in gifted_bad.blocking_issues))

        # Scenario 7: Paid Brand Partnership with Missing Native Toggle -> RED (FR-026)
        paid_no_toggle = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.TIKTOK,
                provenance_status=ProvenanceStatus.PR_GIFTED,
                vault_confidence=VaultConfidenceStatus.UNVERIFIED,
                commercial_relationships=[CommercialRelationship.PAID_PARTNERSHIP],
                caption_text="Ad | Paid partnership with Empyrean Parfums.",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=False,
            )
        )
        self.assertEqual(paid_no_toggle.overall_grade, RiskGrade.RED)
        self.assertTrue(any("NATIVE_TOGGLE_MISSING" in b for b in paid_no_toggle.blocking_issues))

        # Scenario 8: Unverified Self-Purchase ('Experian' merchant awaiting confirmation) -> AMBER
        unverified_experian = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.INSTAGRAM,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.UNVERIFIED,
                commercial_relationships=[CommercialRelationship.NONE],
                caption_text="I bought this perfume myself and these are my personal impressions.",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=False,
                merchant_requires_confirmation=True,
            )
        )
        self.assertEqual(unverified_experian.overall_grade, RiskGrade.AMBER)
        self.assertTrue(any("UNVERIFIED_PURCHASE_PROOF" in w for w in unverified_experian.amber_warnings))

        # Scenario 9: Conflicted Receipt (Refunded / £0 PR Slip) claiming self-purchase -> RED
        conflicted_report = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.TIKTOK,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.CONFLICTED,
                commercial_relationships=[CommercialRelationship.NONE],
                caption_text="Purchased with my own money. These are my personal impressions.",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=False,
            )
        )
        self.assertEqual(conflicted_report.overall_grade, RiskGrade.RED)
        self.assertTrue(any("VAULT_EVIDENCE_CONFLICT" in b for b in conflicted_report.blocking_issues))

        # Scenario 10: Account-Wide 'I never accept gifts' Claim -> RED (Rule G4)
        account_wide_bad = self.preflight.run_preflight(
            PreflightInput(
                platform=PlatformType.INSTAGRAM,
                provenance_status=ProvenanceStatus.SELF_PURCHASED,
                vault_confidence=VaultConfidenceStatus.VERIFIED_SELF_PURCHASE,
                commercial_relationships=[CommercialRelationship.NONE],
                caption_text="I bought this bottle myself. I never accept gifts or sponsorships on this account!",
                hashtags=DEFAULT_FIVE_HASHTAGS,
                native_toggle_enabled=False,
            )
        )
        self.assertEqual(account_wide_bad.overall_grade, RiskGrade.RED)
        self.assertTrue(any("RULE_G4_VIOLATION" in b for b in account_wide_bad.blocking_issues))

    def test_05_anti_spam_ownership_comment_rotation(self) -> None:
        """
        Verify FR-025 & FR-055:
        - Consecutive ownership comments on the same platform never repeat identical wording.
        - Suppressed when any commercial relationship exists.
        """
        pkg1 = self.studio.build_sample_case_a_instagram()
        pkg2 = self.studio.build_sample_case_a_instagram()
        self.assertIsNotNone(pkg1.optional_ownership_comment)
        self.assertIsNotNone(pkg2.optional_ownership_comment)
        self.assertNotEqual(pkg1.optional_ownership_comment, pkg2.optional_ownership_comment)
        self.assertEqual(pkg1.ownership_comment_delivery_mode, "DRAFT_COPY_PASTE")

        # Commercial post suppresses ownership comment
        pkg_comm = self.studio.build_sample_case_b_tiktok(with_affiliate_link=True)
        self.assertIsNone(pkg_comm.optional_ownership_comment)
        self.assertEqual(pkg_comm.ownership_comment_delivery_mode, "SUPPRESSED")

    def test_06_retroactive_receipt_contradiction_guard_fr058(self) -> None:
        """
        Verify FR-058:
        When a post is already published with an `ImmutableEvidenceSnapshot` and a newly imported
        receipt contradicts that published claim (e.g., refund notice arrives), the published snapshot
        is NEVER silently altered, and a `RetroactiveContradictionAlert` is raised.
        """
        # 1. Ingest valid receipt and publish post snapshot
        match_ok = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-SNAP-100\nann@annreveals.co.uk\nCelestial Iris 100ml Extrait £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            raw_order_ref="ORD-SNAP-100",
        )
        self.assertEqual(match_ok.status, VaultConfidenceStatus.VERIFIED_SELF_PURCHASE)

        snapshot = self.vault.create_immutable_snapshot(
            platform="tiktok",
            platform_post_id="tt_video_778899",
            sku="EMP-IRIS-100",
            caption_text="Celestial Iris — Purchased with my own money. These are my personal impressions.",
            selected_disclosures=[],
            native_toggle_enabled=False,
            product_link_present=False,
            provenance_claim="SELF_PURCHASED",
            commercial_relationships=["NONE"],
        )
        original_checksum = snapshot.snapshot_checksum
        self.assertEqual(len(self.vault.contradiction_alerts), 0)

        # 2. Days later, a refund credit note arrives for the same SKU
        refund_match = self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text="Order Ref: ORD-SNAP-100-REFUND\nFULL REFUND ISSUED — Celestial Iris 100ml £195.00",
            merchant_label_raw="Empyrean Parfums",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=0.0,
            raw_order_ref="ORD-SNAP-100-REFUND",
        )
        self.assertEqual(refund_match.status, VaultConfidenceStatus.CONFLICTED)

        # 3. Verify snapshot was NOT silently altered and RetroactiveContradictionAlert was emitted
        stored_snapshot = self.vault.get_snapshot("tiktok", "tt_video_778899")
        self.assertIsNotNone(stored_snapshot)
        assert stored_snapshot is not None
        self.assertEqual(stored_snapshot.snapshot_checksum, original_checksum)
        self.assertEqual(stored_snapshot.vault_status_at_publish, "VERIFIED_SELF_PURCHASE")
        self.assertEqual(len(self.vault.contradiction_alerts), 1)
        alert = self.vault.contradiction_alerts[0]
        self.assertEqual(alert.platform_post_id, "tt_video_778899")
        self.assertEqual(alert.new_vault_status, "CONFLICTED")

    def test_07_violation_intake_automation_freeze_and_redacted_appeal_packet(self) -> None:
        """
        Verify FR-029 to FR-033 and Rule G6:
        - All 9 violation categories supported.
        - Automatic freeze of post automation upon flag (`freeze_post_automation`).
        - Root-cause analysis distinguishes provenance-relevant vs non-provenance flags (e.g. copyright music).
        - Appeal packet strips all PII and requires explicit owner sign-off (`SUBMITTED_BY_USER`).
        """
        # Verify all 9 categories exist
        self.assertEqual(len(list(ViolationCategory)), 9)

        # 1. Ingest receipt with PII and create snapshot
        self.vault.ingest_receipt_for_item(
            sku="EMP-IRIS-100",
            raw_text=(
                "Order Ref: ORD-APPEAL-555\n"
                "Customer: ann@annreveals.co.uk\n"
                "Billing Address: 22 Baker Street, London, NW1 6XE\n"
                "Card: 4532 0151 1283 0366\n"
                "Celestial Iris 100ml Extrait £195.00"
            ),
            merchant_label_raw="Experian",
            extracted_brand="Empyrean Parfums",
            extracted_product_name="Celestial Iris",
            extracted_variant="Extrait",
            extracted_concentration="Extrait de Parfum",
            extracted_size_ml=100,
            subtotal_price=195.00,
            net_paid=195.00,
            owner_verified_merchant=True,
            raw_order_ref="ORD-APPEAL-555",
        )
        snapshot = self.vault.create_immutable_snapshot(
            platform="tiktok",
            platform_post_id="tt_flagged_post_01",
            sku="EMP-IRIS-100",
            caption_text="Celestial Iris — Purchased with my own money. These are my personal impressions.",
            selected_disclosures=[],
            native_toggle_enabled=False,
            product_link_present=False,
            provenance_claim="SELF_PURCHASED",
            commercial_relationships=["NONE"],
        )

        # 2. Intake commercial disclosure violation notice
        self.assertFalse(self.appeals_tracker.is_post_automation_frozen("tiktok", "tt_flagged_post_01"))
        case = self.appeals_tracker.intake_violation(
            platform="tiktok",
            platform_post_id="tt_flagged_post_01",
            reference_code="TT-VIO-2026-8812",
            notification_text="Your video was flagged for undisclosed commercial content / promotional content.",
            snapshot=snapshot,
        )
        # Rule G6: Post automation must be frozen immediately
        self.assertTrue(self.appeals_tracker.is_post_automation_frozen("tiktok", "tt_flagged_post_01"))
        self.assertTrue(case.post_automation_frozen)
        self.assertEqual(case.notice.category, ViolationCategory.COMMERCIAL_DISCLOSURE)
        self.assertTrue(case.root_cause.is_provenance_evidence_relevant)

        # 3. Build Redacted Appeal Packet
        packet = self.packet_builder.build_packet(
            case=case,
            tracker=self.appeals_tracker,
            snapshot=snapshot,
            owner_sign_off_name="Ann (@annreveals)",
        )
        self.assertEqual(case.status, AppealLifecycleStatus.DRAFTED)
        md = packet.to_markdown()
        self.assertIn("Experian", md)  # Raw merchant label preserved in summary
        self.assertIn("Empyrean Parfums", md)  # Canonical name shown
        self.assertNotIn("4532 0151 1283 0366", md)
        self.assertNotIn("22 Baker Street", md)
        self.assertNotIn("NW1 6XE", md)
        self.assertNotIn("ann@annreveals.co.uk", md)
        self.assertFalse(self.redactor.contains_unredacted_pii( packet.redacted_purchase_proof_excerpt))

        # 4. Verify transition to SUBMITTED_BY_USER requires owner_signed_off_by
        with self.assertRaises(ValueError):
            self.appeals_tracker.transition_status(
                case_id=case.case_id,
                new_status=AppealLifecycleStatus.SUBMITTED_BY_USER,
                owner_signed_off_by=None,
            )

        updated_case = self.appeals_tracker.transition_status(
            case_id=case.case_id,
            new_status=AppealLifecycleStatus.SUBMITTED_BY_USER,
            note="Submitted manually in TikTok Studio app.",
            owner_signed_off_by="Ann (@annreveals)",
        )
        self.assertEqual(updated_case.status, AppealLifecycleStatus.SUBMITTED_BY_USER)

        # 5. Also verify non-provenance violation (e.g., copyright_music) distinguishes root cause
        music_case = self.appeals_tracker.intake_violation(
            platform="instagram",
            platform_post_id="ig_reel_music_99",
            reference_code="IG-MUS-404",
            notification_text="Audio muted due to copyright music rights restriction.",
        )
        self.assertEqual(music_case.notice.category, ViolationCategory.COPYRIGHT_MUSIC)
        self.assertFalse(music_case.root_cause.is_provenance_evidence_relevant)
        self.assertTrue(self.appeals_tracker.is_post_automation_frozen("instagram", "ig_reel_music_99"))


if __name__ == "__main__":
    unittest.main()
