"""Install the application in a private environment and serve local drafts."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
INTERPRETER = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> int:
    os.chdir(ROOT)
    verify = len(sys.argv) == 2 and sys.argv[1] == "verify"
    if len(sys.argv) > 1 and not verify:
        print("Use this launcher without arguments, or with verify.", file=sys.stderr)
        return 2
    entry = ["scripts/verify_local.py"] if verify else ["-m", "backend.main"]
    uv = shutil.which("uv")
    local_uv = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
    if uv is None and os.access(local_uv, os.X_OK):
        uv = str(local_uv)
    # A managed Python has matching published cryptography wheels on Intel Macs.
    if uv:
        command = [
            uv, "run", "--no-project", "--python", "3.11",
            "--with-requirements", str(ROOT / "requirements.txt"),
            "python", *entry,
        ]
    else:
        if sys.version_info < (3, 11) or sys.version_info >= (3, 15):
            print("Install Python 3.11–3.14 or uv, then open the launcher again.", file=sys.stderr)
            return 2
        if not INTERPRETER.exists():
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True, timeout=60)
        subprocess.run(
            [str(INTERPRETER), "-m", "pip", "install", "--disable-pip-version-check",
             "-r", str(ROOT / "requirements.txt")],
            check=True, timeout=240,
        )
        command = [str(INTERPRETER), *entry]
    environment = dict(os.environ, HOST="127.0.0.1", PORT="8080")
    environment.setdefault("TIKTOK_WRITE_ENABLED", "false")
    if not verify:
        print("Open http://127.0.0.1:8080 in your browser. Close this window to stop the app.", flush=True)
    return subprocess.call(command, env=environment)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.TimeoutExpired:
        raise SystemExit("Dependency installation timed out. Check the connection and open the launcher again.")
    except subprocess.CalledProcessError:
        raise SystemExit("Dependency installation failed. See the message above and open the launcher again.")
    except KeyboardInterrupt:
        raise SystemExit(0)
