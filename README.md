# Ann Reveals AI Manager

An installable web dashboard for preparing TikTok and Instagram replies, recording redacted purchase evidence, and managing a verified TikTok Business account connection.

The app works locally for comments you paste from your posts. It classifies the comment, uses public facts you have confirmed for that post, and produces a draft with copy and open-post actions. Sensitive or unsupported questions are marked for your review.

Automatic TikTok comment reading and replies use the official Business Accounts API. They require TikTok's approval, a provider-issued token for the configured app and owner account, an authenticated HTTPS deployment, and an owner-selected pilot reply. The software reports a successful reply only after TikTok supplies a reply identifier. Uncertain sends are reconciled from provider replies before further action.

## Run locally

Unzip the source package and open `Start-Ann-Reveals.command` on macOS or `Start-Ann-Reveals.bat` on Windows. The launcher uses an existing `uv` installation or Python 3.11–3.14 to install the pinned dependency into an isolated environment. On Intel macOS, `uv` can supply Python 3.11 with a compatible encryption wheel.

Open <http://127.0.0.1:8080>. Keep the launcher window open while using the local app. Initial dependency installation needs an internet connection. For a hosted app, use the hosting service's HTTPS address.

The app stores its local database and a private encryption key under `data/`. Back up that directory and keep it private. With `ARAIM_MASTER_KEY` configured, retain that secret for restore.

## Use the app

1. Open Comments Inbox and paste your post's full URL and a comment.
2. Add any notes, measured wear test, public price or retailer you have checked for that exact post. Confirm the facts before using them.
3. Prepare the draft, review the result, copy it and open the post.
4. In Purchases Vault, paste text from an actual receipt with the product and merchant details. The app redacts personal information and stores the record encrypted.
5. Create an encrypted backup from Settings. The app uses a consistent SQLite snapshot and verifies its restore.

## Hosted installation and TikTok connection

Follow `installers/INSTALL_GUIDE_WINDOWS_AND_ANDROID.md` for Docker or PaaS configuration and Android/desktop PWA installation. The manifest, icons, service worker and offline page are served by the Python application. The portable HTML file is a demonstration file.

Supply approved TikTok Business credentials through the hosting service's private environment. `.env.example` lists the supported names. A submitted form cannot grant OAuth or API approval. Verify the connection in the dashboard, sync owned-video comments, review the exact stored reply and target for a pilot, then enable automatic replies for eligible new comments.

Token expiry or revoked access returns the app to a pending/reconnect state. Automatic Accounts token renewal and managed OAuth onboarding remain open. Third-party creator engagement uses manual drafts.

## Verification and remaining requirements

The local tests cover provider wire contracts, durable dispatch and restart recovery, webhook validation, owner HTTP access, manual drafting, receipt persistence, AES-GCM migration and backup restore. The web tests cover connection states, draft controls, escaped social content and PWA caching.

Open `Verify-Ann-Reveals.command` on macOS or `Verify-Ann-Reveals.bat` on Windows to run the available checks and save their logs. Dashboard tests require Node.js. Live social credentials are removed from the verification subprocess environment.

Use a Python environment with `requirements.txt` installed.

```bash
python -m unittest discover -s tests -t . -p 'test_*.py' -v
node --test tests/web/*.test.cjs
```

See `docs/IMPLEMENTATION_STATUS.md` for all 58 functional and 10 non-functional requirements and their remaining acceptance work. Live TikTok posting, managed cloud deployment and physical-device installation require external setup and verification.
