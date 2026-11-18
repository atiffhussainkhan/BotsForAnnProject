# Install Ann Reveals AI Manager

One hosted Ann Reveals AI Manager instance serves the dashboard, comment worker and private records. Install its web app on each device from the same private HTTPS address.

## Windows or Mac laptop

1. Open the hosted address in Chrome or Microsoft Edge.
2. Sign in with your Ann Reveals owner credentials.
3. Choose **Install App** in the dashboard when the browser offers it. You can also open Chrome’s **Cast, save and share** menu or Edge’s **Apps** menu and use the browser’s install command.
4. Open **Ann Reveals** from your applications or Start menu. The installed app uses the hosted dashboard and data.

On Windows, `windows/Start-AnnReveals-Windows.bat` can also add URL shortcuts for the hosted service to the Desktop and Start menu. Enter the address supplied by the administrator. Use the browser’s install command if you want the standalone app window.

## Android phone

1. Open the same **HTTPS** address in Chrome and sign in.
2. Tap **Install App** in the dashboard or open Chrome’s menu and select **Add to Home screen** or **Install app**.
3. Open the **Ann Reveals** icon. The app can show an offline page when the server is unreachable. Account and comment operations need a connection to the server.

The repository’s portable HTML file is an offline demonstration. Use the hosted address for the operational dashboard.

## Run a local preview

Open the root `Start-Ann-Reveals.command` on macOS or `Start-Ann-Reveals.bat` on Windows. For a Python 3.11–3.14 environment you manage yourself, install the requirements and launch the application from the repository root.

```bash
python3 -m pip install -r requirements.txt
HOST=127.0.0.1 PORT=8080 python3 -m backend.main
```

Open `http://127.0.0.1:8080`. To use Docker Compose on your development machine, set a private `ARAIM_OWNER_PASSWORD` of at least 20 characters, run `docker compose up --build`, sign in as `owner`, and open `http://127.0.0.1:8000`. That preview publishes to loopback and starts with live writes disabled.

## Host the service

The container builds from the repository root using `infra/docker/Dockerfile`. Use one instance with a persistent disk on `/app/data`. Ensure the disk is writable by application UID and GID `10001`. The application database and backups are stored at `/app/data/database/ann_reveals_manager.db` and `/app/data/backups`. Use `GET /api/v1/health` as the health probe.

Configure the public HTTPS origin as `ARAIM_PUBLIC_ORIGIN`, set a unique `ARAIM_OWNER_PASSWORD` of at least 20 characters, and supply a stable high-entropy `ARAIM_MASTER_KEY` through the host’s secret settings. The default username is `owner`, or set `ARAIM_OWNER_USERNAME`. Configure the TLS proxy to retain the publicly configured hostname.

The Fly manifest is under `infra/deploy/fly.toml` and is intended for a deployment from the repository root. Render can use `infra/deploy/render.yaml` as a custom Blueprint path. These are deployment configurations. The owner needs the actual hosted address before installing the app.

## Connect TikTok

1. The administrator configures the authorised TikTok for Business account in the host’s secret settings with `TIKTOK_BUSINESS_APP_ID`, `TIKTOK_BUSINESS_OPEN_ID`, and `TIKTOK_BUSINESS_ACCESS_TOKEN`. Start with `TIKTOK_WRITE_ENABLED=false`.
2. Use **Verify TikTok connection** in the dashboard. After TikTok confirms the connection, check the inbox for a draft on one of your own videos.
3. To pilot one public reply, enable `TIKTOK_WRITE_ENABLED=true` on the authenticated HTTPS deployment and restart the instance. Keep the dashboard in Draft mode. Review a displayed draft and confirm **Send this pilot reply** when you are ready.
4. After TikTok confirms the pilot, choose **Automatic replies for eligible comments**. Use the dashboard to review drafts, check the latest sync, switch back to Draft or Off, and pause outgoing replies.

When TikTok access or reply permission is unavailable, keep the connection in Draft mode. The dashboard shows the provider check status and lets the owner use drafts for manual posting.
