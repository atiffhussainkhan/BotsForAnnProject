# Continue Ann Reveals in Gemini / Antigravity

Paste the complete prompt below into Antigravity with the GitHub repository selected. The published `main` revision supplied in the accompanying handoff is the starting point. The tested application repair is commit `fa7124877b92a2029173134787aa98aea01e45ff`.

---

Continue developing **Ann Reveals AI Manager** from `https://github.com/atiffhussainkhan/BotsForAnnProject`. Carry the implementation through testing, review, and a reviewable commit. Start by reading the current code and requirements, then make the necessary changes.

The owner wants an installable professional app that prepares and sends appropriate replies to comments on their own TikTok posts, verifies the outcome, and operates continuously. The owner also asked for automatic posting without API access and completion of OAuth token renewal. Establish the supported access route first. OAuth access tokens authorize API calls, so implementing OAuth renewal uses an API integration. The existing official TikTok Business Accounts comment route requires provider-approved access. Code and local tests cannot supply that permission. [TikTok Accounts API overview](https://business-api.tiktok.com/portal/docs/accounts-api-overview/v1.3)

Check the current official TikTok documentation and identify any supported route that satisfies the owner's requested account type and actions. Cite the exact official documentation, permissions, and limits. If an approval-free route is available, prove its documented capability and explain its prerequisites before choosing it. If the requested combination has no supported route, say so plainly and continue completing the app features that can run locally. The owner can use the existing imported-comment drafting and copy/open workflow while access is pending. The owner's latest request includes evaluating operation without a developer API approval. Record any departure from the original PRD and verify the supported authentication method, capabilities and limits. OAuth renewal belongs to an API integration. Any approval-free route needs its own evidence of supported access and a real publishing outcome.

## Baseline already delivered

Codex committed the application repairs in `fa7124877b92a2029173134787aa98aea01e45ff`. The repository handoff may have a later documentation commit. Fetch current `main`, record its exact SHA, and verify that the repair commit is in its ancestry. Review any later code changes before relying on the earlier evidence.

The repair revision passed **77 Python tests and six dashboard/PWA tests**, with 64 Python files parsed. Local browser verification exercised imported-comment drafts, owner-confirmed fragrance notes, receipt PII redaction, encrypted purchase storage, backup/restore, and persistence after a server restart. The tested app used Python 3.11.17 on Intel macOS. Live TikTok posting, cloud deployment, and physical Android/Windows installation were unverified.

The delivered application already contains these working features.

- An HTTP-served PWA with real HTML, manifest, PNG icons, service worker and an offline page.
- Manual comment import, 14-category classification, safe drafts grounded in facts confirmed for the exact post, and copy/open controls.
- Private receipt storage with AES-GCM envelopes and compatibility reads for legacy encrypted records.
- A TikTok Business token inspector that checks provider app/account identity and returned scopes.
- Owned-video/comment pagination, signed webhook wakeups and a persistent SQLite inbox.
- Atomic reply claims, provider reply identifiers, uncertain-outcome readback, duplicate-text checks and emergency-stop controls.
- Warning freezes persisted across restart and rechecked immediately before dispatch.
- Repeatable launchers and a discoverable GitHub Actions workflow.

The complete PRD remains partially fulfilled. Use `docs/IMPLEMENTATION_STATUS.md` as the current acceptance record, and retain the original requirement IDs.

## Read these files first

Read applicable `AGENTS.md` instructions and these repository files:

- `README.md`
- `docs/PRD.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/TRACEABILITY_MATRIX.md`
- `docs/API_CAPABILITY_MATRIX.md`
- `docs/ACCESS_READINESS.md`
- `installers/INSTALL_GUIDE_WINDOWS_AND_ANDROID.md`
- `backend/main.py`
- `backend/tiktok_worker.py`
- `backend/comment_drafts.py`
- `apps/backend/integrations/tiktok/adapter.py`, `models.py`, `webhook.py`, and `tiktok-capabilities.json`
- `apps/backend/platform_ops/security.py`
- `apps/backend/provenance/storage.py` and `vault.py`
- `.env.example`, `requirements.txt`, `scripts/start_local.py`, and `scripts/verify_local.py`

Prior completion reports contain historical sandbox claims. Confirm the actual entry point, provider call, stored state, and visible UI for each requirement you close.

## Prepare and verify the checkout

For a fresh checkout in a new directory, the following Bash establishes the tested ancestry and a separate branch. If a checkout already contains work, inspect it and create a separate worktree so those changes stay recoverable.

```bash
set -eu
git clone https://github.com/atiffhussainkhan/BotsForAnnProject.git
cd BotsForAnnProject
git fetch origin main
required='fa7124877b92a2029173134787aa98aea01e45ff'
base="$(git rev-parse origin/main)"
git merge-base --is-ancestor "$required" "$base"
expected_handoff="${ARAIM_HANDOFF_COMMIT:-}"
if [ -n "$expected_handoff" ]; then
  git merge-base --is-ancestor "$expected_handoff" "$base"
fi
branch="finish/tiktok-integration-$(date -u +%Y%m%dT%H%M%SZ)"
git switch -c "$branch" "$base"
printf 'Starting commit %s\nWorking branch %s\n' "$base" "$branch"
python3 scripts/start_local.py verify
```

Set `ARAIM_HANDOFF_COMMIT` to the uploaded handoff commit named in the publication confirmation when you also want to verify that documentation revision is present. Leave it unset to verify the repair ancestry and record current `main`.

The launcher uses `uv` when available, or Python 3.11–3.14 and a local virtual environment. Node.js runs the dashboard tests. A missing runtime or dependency installation failure needs a specific diagnosis. Keep test failures, environment failures, and timeouts distinguishable. The verification launcher removes live social credentials from its test subprocesses and writes its evidence directory to the console.

The direct checks in an environment with `requirements.txt` installed are:

```bash
python -m unittest discover -s tests -t . -p 'test_*.py' -v
node --test tests/web/*.test.cjs
```

Preserve these assertions. Add focused regression coverage for the behavior you change.

## Complete the TikTok access lifecycle

1. Determine which TikTok product and authorization flow covers owned-post comment reading and replies. Verify the current Business Accounts authorization, token exchange, token introspection, refresh, revocation, and comment contracts from primary sources. The existing `refresh_auth` method also contains legacy generic Login Kit / Content Posting API behavior. Check its API family before wiring it to the Business worker.
2. Implement a real owner onboarding route with an approved application configuration. Use exact registered redirect validation, one-use expiring state, and PKCE where the selected provider flow defines it. Store server-side secrets in the hosting secret manager. Store acquired grants encrypted with the existing AES-GCM service and bind them to provider, application and owner identity. Display a clear provider-backed connection state.
3. Add expiry tracking and serialized refresh so concurrent worker/request activity performs one renewal. Persist rotated credentials atomically, retain working state if storage fails, refresh before expiry according to the documented contract, and re-inspect account identity and scopes after renewal. Test rotated refresh tokens, timeouts, malformed responses, revoked grants, insufficient scopes, restart and simultaneous refresh attempts. If a refresh outcome is uncertain, preserve a recoverable state and avoid an uncontrolled retry loop.
4. Make token expiry and revocation visible in the dashboard and audit trail. A reconnect action must perform the real authorization sequence. Browser-submitted booleans must never manufacture OAuth approval or a live badge.
5. Integrate the confirmed token lifecycle with `TikTokWorker`. Preserve durable comment identity, pagination progress, frozen posts, emergency stop, quiet hours, action limits, duplicate protection and uncertain-send reconciliation. Recheck eligibility at the outbound boundary. Count a reply as sent only with a confirmed provider identifier or a matching provider readback.
6. Keep comments on other creators' posts in the supported manual workflow unless a documented and authorized interaction capability has been established for that action.

No secrets, access tokens, refresh tokens, owner passwords, receipts or browser sessions belong in Git history, test fixtures, screenshots or a public report. Use private configuration and synthetic values in tests. Scrub provider error payloads before logging them.

## Complete the app work that remains independent of access approval

Use the current requirement matrix to prioritize the remaining implementation. Work through complete user flows with persistent state.

- Complete product editing and associations between real owned posts, multiple products, public facts and purchase evidence. Preserve the distinction between private purchase price and owner-approved public price. Keep unmeasured wear time and unknown provenance explicit.
- Persist creator watchlists, reminders and appeal case records. Keep warning freezes effective across restart and preserve prior evidence snapshots when a later receipt contradicts a published claim.
- Add validated PDF/image receipt extraction with PII redaction before persistence or model access. Give the owner a correction step for uncertain text, merchant identity, product matching and confidence. Use actual input evidence throughout the normal upload path.
- Finish scheduled backups, retention cleanup, data export/erasure and operational notifications across the stores actually used by the app. Prove restoration with a consistent database snapshot and retained encryption keys.
- Complete useful owner controls for retries and failed/pending work. An uncertain outgoing reply must go through reconciliation before a resend decision.
- Keep the normal dashboard usable while external capabilities await approval. Preserve manual import, grounded drafts, copy/open actions and honest status labels.
- Review dependency compatibility, vulnerability checks, secret scanning, migrations, error handling and CI. Keep changes focused on requirements and preserve existing callers and saved data.

## Verify installation and a controlled live pilot

Use an authenticated HTTPS instance with persistent storage for the hosted app. Follow the existing Docker/PaaS configuration, confirm owner authentication and same-origin protections, and verify the actual served revision. Verify manifest, icons, service worker and offline behavior from the deployed address. Test Android Home Screen and desktop browser installation on the devices you actually have, and label device coverage accurately.

Before a real public test reply, present the exact owner account, owned video URL, comment ID, and reply text and obtain approval for that specific test. The current instruction is to continue development and verification. Use mocked transport and synthetic fixtures until the controlled pilot is authorized and provider access is available.

For the authorized pilot, confirm the provider account and scopes, sync a real owned comment, display the stored draft, send it once, and read the result back from TikTok. Retain the provider reply identifier and an owner-visible link or equivalent evidence. Check token renewal and a subsequent sync across an application restart. Exercise Off/Draft/SAFE_AUTO controls and emergency stop without creating extra public test replies. Never infer live success from a local counter, test fixture or HTTP 200 alone.

A video/photo publication workflow uses a separate capability from comment replies. Establish which action the owner means before extending publication beyond replies to their existing posts. Verify that action's product, permissions, review conditions and asynchronous outcome separately.

## Review and final delivery

Run the existing suite and the new regression checks on the final clean commit. Verify the user-facing flows through their normal entry points and inspect meaningful screenshots. Obtain an independent code review, fix concrete findings and rerun affected checks. If a reviewer or external provider is unavailable, retain the exact error and record the remaining acceptance item.

Update `docs/IMPLEMENTATION_STATUS.md` requirement by requirement with source paths, tests and observed results. Distinguish local tests, mocked-provider tests, a hosted browser run, device installation and a live TikTok test. Record exact commit, branch, environment, test counts, intentional skips, remaining gaps and evidence paths. State configured estimates and measured operational values accurately.

Deliver a reviewable implementation commit, concise release notes, repeatable setup and verification commands, and a candid completion report. Fully automatic operation is complete only after the required provider access, unattended credential lifecycle and controlled live results have been verified. Continue the independent implementation work while an external approval is pending, and end with the precise external action the owner needs to take.
