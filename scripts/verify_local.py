"""Run local checks and retain their results without contacting social accounts."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    evidence = Path(tempfile.mkdtemp(prefix="ann-verification-"))
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("TIKTOK_", "INSTAGRAM_", "THIRD_PARTY_"))
        and key not in {"ARAIM_MASTER_KEY", "ARAIM_PUBLIC_ORIGIN", "ARAIM_OWNER_PASSWORD",
                        "ARAIM_DB_PATH", "ARAIM_BACKUP_DIR", "ARAIM_DEMO_MODE"}
    }
    environment.update(
        TIKTOK_WRITE_ENABLED="false", INSTAGRAM_WRITE_ENABLED="false",
        THIRD_PARTY_AUTOCOMMENT="false", PYTHONDONTWRITEBYTECODE="1",
    )
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "source-package"
    checks = [
        ("python-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", "test_*.py", "-v"]),
    ]
    node = shutil.which("node")
    if node:
        checks.append(("web-tests", [node, "--test", *map(str, sorted((ROOT / "tests/web").glob("*.test.cjs")))]))
    results = []
    for name, command in checks:
        log = evidence / f"{name}.log"
        print(f"Running {name}. Log saved to {log}", flush=True)
        with log.open("w") as output:
            try:
                completed = subprocess.run(
                    command, cwd=ROOT, env=environment, stdout=output,
                    stderr=subprocess.STDOUT, timeout=240,
                )
                code = completed.returncode
            except subprocess.TimeoutExpired:
                code = 124
            except OSError as error:
                output.write(str(error))
                code = 126
        results.append({"check": name, "exit_code": code, "log": str(log)})
        print(f"{name} {'passed' if code == 0 else 'failed'} ({code})", flush=True)
    if not node:
        results.append({"check": "web-tests", "exit_code": 127, "reason": "Node.js is required for dashboard tests."})
    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "revision": revision,
        "python": platform.python_version(),
        "system": platform.platform(),
        "cryptography": importlib.metadata.version("cryptography"),
        "checks": results,
        "provider_calls": "Live TikTok and Instagram verification requires a separately configured account.",
    }
    (evidence / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Results saved to {evidence / 'results.json'}", flush=True)
    return int(any(result["exit_code"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
