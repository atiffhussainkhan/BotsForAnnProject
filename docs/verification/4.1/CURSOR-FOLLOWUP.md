**Scoped closure** on the two important findings, based on the supplied worker code.

**SENT without ID** — Closed. Durable `SENT` requires `result.ok`, `dispatch_state == SENT`, and a non-empty `data.comment_id`. `SENT` (or missing `data`) without an ID lands in `RECONCILE_PENDING`, not `SENT`.

**Unknown outgoing / anti-duplicate (NFR03)** — Closed in this path. Ambiguous and exception outcomes become `RECONCILE_PENDING` (or stay `SENDING`); `_reconcile` only promotes to `SENT` on a matching self-reply and never re-invokes `reply_to_owned_comment`. Similarity collisions flip to `NEEDS_HUMAN_REVIEW` inside `BEGIN IMMEDIATE` before the claim-to-`SENDING` update. Freeze / write gates still short-circuit to `DRAFT_READY` before send.

**No definite important remainder in this snippet.** Residual notes are scoped, not reopeners: definitive non-`SENT`/`RECONCILE_PENDING` provider outcomes map to `FAILED` and are outside the reconcile select (fine if those are true failures only); `has_more` keeps `DRAFT_READY` rather than the review queue named in the comment (still refuses to send); unexpected exceptions after the `SENDING` commit leave the row for reconcile rather than auto-resend.

Environment-bound gaps (TikTok write approval, full automatic posting) remain candidly partial outside this closure.
