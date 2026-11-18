# Ann Reveals AI Manager 4.1 delivery

Clone the repository or download its source archive, open the source folder, and open `Start-Ann-Reveals.command` on macOS or `Start-Ann-Reveals.bat` on Windows. Then open `http://127.0.0.1:8080`. The first launch installs the pinned encryption dependency. The launcher supports an existing uv installation or Python 3.11–3.14.

The tested implementation is commit `fa7124877b92a2029173134787aa98aea01e45ff`. The Antigravity continuation prompt is in `docs/ANTIGRAVITY-HANDOFF.md`. This verification folder records the tested implementation.

## Working local features

- Paste a comment and the link to your TikTok or Instagram post. The app classifies the comment, prepares a reply, and offers copy and open-post controls.
- Confirm public fragrance notes, measured wear-test details, price or retailer for that exact post. Replies use those recorded facts. Sensitive and unsupported questions enter owner review.
- Store actual receipt text with product details. Personal information is redacted before storage, and the purchase vault persists with AES-GCM encryption.
- Create a consistent SQLite backup, encrypt it, and verify its restoration. Drafts and purchase records survived a real server restart.
- Use the repaired dashboard, install manifest, PNG icons, service worker and offline page. The owner dashboard requires authentication on network/container listeners.
- Run `Verify-Ann-Reveals.command` or `Verify-Ann-Reveals.bat` to repeat the automated checks. Dashboard tests require Node.js.

## Official automatic TikTok workflow

The code includes provider token/app/account verification, paginated owned-comment polling, signed webhook wakeups, persistent comment state, an explicit owner-selected pilot, mode and emergency-stop controls, and reply identifiers confirmed by TikTok.

Uncertain sends stay pending for provider readback. Post-warning freezes survive restart and are rechecked before dispatch. Repeated response text is held for review.

TikTok requires approved Accounts API access for official automatic reading and posting. This account access was unavailable for live verification. Automatic Business token renewal and managed OAuth onboarding also remain open. Without that access, the delivered workflow prepares imported comment drafts for manual posting.

## Verification on the delivered commit

| Check | Result |
| --- | --- |
| Python suite | 77 passed, zero failures |
| Dashboard and PWA suite | 6 passed, zero failures |
| Python syntax | 64 files parsed |
| Dependency compatibility | Passed |
| Real HTTP resources | Eight routes returned expected bodies and MIME types |
| Real browser | Manual drafts, confirmed product notes, redacted receipt storage and backup/restore checked with zero observed console errors |
| Restart persistence | Imported comments, public post facts and encrypted purchase records restored |
| Archive | ZIP integrity, required launchers, executable permission and exclusion of private runtime/build data checked |

The normal verification launcher passed on the delivered commit and retained separate logs. `verification.json`, `python-tests.log`, `web-tests.log`, and `http-verification.json` contain the results.

Cursor reviewed the code and closed the confirmed-send identifier and uncertain-outcome findings in a follow-up. An independent local review also found and prompted fixes for persistent post freezes, reconciliation fairness, duplicate response text, and a freeze during provider readback. Their regression tests passed on the final commit.

## Remaining requirements

`Requirements Status.md` and the source file `docs/IMPLEMENTATION_STATUS.md` assess every original requirement. The whole PRD remains partially fulfilled. Remaining work includes live provider verification, managed OAuth and token renewal, complete Instagram live integration, automated PDF/image OCR, full persistence for watchlists and appeal cases, comprehensive retention/erasure and notifications, and actual cloud/device deployment verification.

Container and Windows installer execution were unavailable in this environment. GitHub Actions is now configured in the correct location, while a hosted run on this candidate remains unverified. Budget numbers in the dashboard are configured estimates.

The candidate was developed in a separate local clone. The original checkout and its existing local change were preserved.
