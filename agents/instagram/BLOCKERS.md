# Agent Bravo (Instagram) — External Blockers & Dependency Register

**Agent:** Agent Bravo (Agent 2 — Meta/Instagram Developer Platform & Integrations Specialist)  
**Last Updated:** 27 October 2026  
**Current Live Connection Status:** `NOT_CONNECTED` (`Awaiting owner OAuth connection` / `DRAFT_ONLY`)

---

## Active External Blockers (Owner / Meta Platform Gate)

| Blocker ID | Severity | Category | Description | Required Action by Owner (`@annreveals`) | Fallback Active in Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BLK-IG-001** | **EXTERNAL_GATE** | Professional Account Prerequisite | `@annreveals` must be configured as an Instagram **Professional Account** (**Creator** or **Business**) in the Instagram mobile app. Personal Instagram accounts cannot access the Instagram Graph API. | In Instagram app: `Settings and activity -> Account type and tools -> Switch to professional account -> Creator`. Takes ~2 minutes, free. | Adapter reports `Not connected` and keeps all Instagram workflows in `DRAFT_ONLY` / manual copy mode. |
| **BLK-IG-002** | **EXTERNAL_GATE** | Meta Developer App & OAuth Credentials | Live `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, and `INSTAGRAM_WEBHOOK_VERIFY_TOKEN` have not yet been provisioned from a live Meta App Dashboard for `@annreveals`. | Create Meta Business App in `developers.facebook.com`, add the **Instagram** product ("API setup with Instagram login"), add `@annreveals` as an **Instagram Tester**, and click **Connect Instagram** in ARAIM settings. | Deterministic sandbox mock mode & offline contract fixtures allow 100% local/CI verification without live secrets. |
| **BLK-IG-003** | **EXTERNAL_GATE** | Live Comment Write Gate (`INSTAGRAM_WRITE_ENABLED`) | Outgoing comment creation (`POST /{ig-comment-id}/replies` and `POST /{ig-media-id}/comments`) requires live verification of `instagram_business_manage_comments` scope and explicit owner activation after a 10-comment pilot test. | Complete OAuth grant, verify scopes in Dashboard (`Connected: read only` -> `Live: can reply`), review 10 drafted replies in `DRAFT` mode, then toggle `INSTAGRAM_WRITE_ENABLED=true`. | `INSTAGRAM_WRITE_ENABLED=false` is enforced by default; all generated replies are saved as reviewable drafts with one-tap copy. |
| **BLK-IG-004** | **PERMANENT_PLATFORM_LIMIT** | Non-Owned Post Commenting & Following Feed | Meta's official Instagram Platform API does **not** permit listing an account's following feed or posting comments on other creators' posts via API. | None (platform architectural boundary). Use the ARAIM **Creator Engagement Assistant** notification + one-tap "Copy Comment & Open Instagram" workflow. | `comment_on_nonowned_post()` and `get_following_posts()` permanently raise `UnsupportedCapabilityError` (`THIRD_PARTY_AUTOCOMMENT=false`). |

---

## Non-Blockers (Resolved in Engineering)
- **Webhook HMAC-SHA256 Security:** Implemented and unit-tested in `apps/backend/integrations/instagram/webhook.py`.
- **Duplicate Reply Prevention on Network Timeout:** Implemented via `RECONCILE_PENDING` check against `GET /{ig-comment-id}/replies` before any retry in `apps/backend/integrations/instagram/adapter.py`.
- **Self-Reply Loop Prevention:** Implemented in both webhook ingestion and adapter dispatch (`author_id == owner_id` or `author_username == "annreveals"` is strictly skipped).
