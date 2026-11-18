"""Prepare grounded comment drafts from owner-supplied posts and public facts."""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
import sqlite3
from urllib.parse import urlsplit

COMPLIMENT_REPLIES = (
    "Thank you for such a lovely comment!",
    "I really appreciate you taking a moment to say that. Thank you!",
    "So kind of you to leave this. Thank you for watching!",
    "What a lovely thing to read today. Thank you!",
    "Thank you for being here and for saying something so kind!",
    "That's so thoughtful of you. I'm glad you enjoyed the video!",
    "Your kind words mean a lot. Thank you for watching!",
    "I'm so glad you enjoyed it. Thank you for the lovely comment!",
)



def owned_post_url(platform: str, value: str) -> tuple[str, str]:
    url = urlsplit(value.strip())
    allowed = {
        "tiktok": {"tiktok.com", "www.tiktok.com"},
        "instagram": {"instagram.com", "www.instagram.com"},
    }
    parts = url.path.strip("/").split("/")
    valid = (
        platform == "tiktok" and len(parts) == 3 and parts[0].startswith("@")
        and parts[1] == "video" and parts[2].isdigit()
    ) or (
        platform == "instagram" and len(parts) == 2
        and parts[0] in {"p", "reel"} and parts[1].replace("_", "").replace("-", "").isalnum()
    )
    if (not valid or url.scheme != "https" or url.hostname not in allowed.get(platform, set())
            or url.username or url.password or url.port not in (None, 443)):
        raise ValueError("Use the full HTTPS link to the TikTok video or Instagram post.")
    return f"https://{url.hostname}{url.path.rstrip('/')}/", parts[-1]


def grounded_draft(classification, facts: dict, comment_id: str) -> str | None:
    if classification.risk_tier != "SAFE" or classification.needs_human:
        return None
    category = classification.category
    if category == "compliment":
        digest = hashlib.sha256(comment_id.encode()).digest()
        return COMPLIMENT_REPLIES[digest[0] % len(COMPLIMENT_REPLIES)]
    # These facts are explicitly confirmed by the owner for this exact post.
    if not facts:
        return None
    if category == "product_notes" and facts.get("notes"):
        return f"The notes I recorded for this fragrance are {facts['notes']}."
    if category == "longevity":
        if facts.get("wear_test"):
            return f"In my recorded wear test, {facts['wear_test']}. Wear can vary with skin and conditions."
        return "I haven't recorded a full wear test for this one yet, so I can't give a measured wear time."
    if category == "price" and facts.get("public_price"):
        return f"The price I recorded is {facts['public_price']}. Please check the retailer for the current price."
    if category == "where_to_buy" and facts.get("retailer"):
        return f"The retailer I recorded for this fragrance is {facts['retailer']}."
    return None


class CommentDrafts:
    def __init__(self, app):
        self.app = app
        self.path = app.db.db_path
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS owner_post_facts (
                    platform TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    post_url TEXT NOT NULL,
                    facts_json TEXT NOT NULL,
                    PRIMARY KEY (platform, post_id)
                );
                CREATE TABLE IF NOT EXISTS imported_comment_links (
                    comment_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    post_url TEXT NOT NULL
                );
            """)

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def facts_for(self, platform, post_id) -> dict:
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT facts_json FROM owner_post_facts WHERE platform=? AND post_id=?",
                (platform, post_id),
            ).fetchone()
        return json.loads(row[0]) if row else {}

    def import_comment(self, payload) -> dict:
        platform = str(payload.get("platform", "tiktok")).lower()
        post_url, post_id = owned_post_url(platform, str(payload.get("post_url", "")))
        raw = str(payload.get("comment_text", "")).strip()
        if not raw or len(raw) > 5000:
            raise ValueError("Paste a comment of up to 5,000 characters.")
        text = self.app.redactor.redact(raw).redacted_text
        author = self.app.redactor.redact(str(payload.get("author_handle") or "Imported viewer")[:100]).redacted_text
        comment_id = "import-" + hashlib.sha256(f"{platform}:{post_id}:{author}:{text}".encode()).hexdigest()[:28]
        if payload.get("facts_confirmed") is True:
            supplied = payload.get("facts") or {}
            if not isinstance(supplied, dict):
                raise ValueError("Public facts must be an object.")
            facts = {}
            for field in ("notes", "wear_test", "public_price", "retailer"):
                value = supplied.get(field, "")
                if not isinstance(value, str) or len(value) > 400:
                    raise ValueError("Each public fact can contain up to 400 characters.")
                facts[field] = self.app.redactor.redact(value.strip()).redacted_text
            with closing(self.connect()) as db, db:
                db.execute(
                    """INSERT INTO owner_post_facts VALUES (?, ?, ?, ?)
                       ON CONFLICT(platform,post_id) DO UPDATE
                       SET post_url=excluded.post_url, facts_json=excluded.facts_json""",
                    (platform, post_id, post_url, json.dumps(facts)),
                )
        facts = self.facts_for(platform, post_id)
        classification = self.app.classifier.classify(text, author_handle=author)
        candidate = grounded_draft(classification, facts, comment_id)
        status = (
            "BLOCKED_SAFETY_GUARD" if classification.risk_tier == "BLOCK"
            else "IMPORTED_DRAFT" if candidate else "NEEDS_HUMAN_REVIEW"
        )
        audit = ["Owner imported comment", f"Classified as {classification.category}",
                 "Public facts confirmed by owner" if facts else "No confirmed product facts",
                 "Draft prepared for manual review" if candidate else "Owner review required"]
        self.app.db.save_comment(
            comment_id, platform, post_id, author, text, classification.category,
            classification.risk_tier, status, candidate, audit,
        )
        with closing(self.connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO imported_comment_links VALUES (?, ?, ?)", (comment_id, platform, post_url))
        return {
            "accepted": True, "comment_id": comment_id, "platform": platform,
            "response_status": status, "category": classification.category,
            "reply_candidate": candidate, "post_url": post_url,
        }

    def attach_links(self, comments):
        with closing(self.connect()) as db:
            links = {cid: url for cid, url in db.execute("SELECT comment_id, post_url FROM imported_comment_links")}
        for comment in comments:
            comment["post_url"] = links.get(comment["provider_comment_id"], "")
        return comments
