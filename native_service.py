"""Start a native development API/identity worker with a private environment file.

LaunchAgents invoke this entry point from the consolidated OLDAP checkout.
Only loopback listeners are used; secrets never enter command arguments.
"""
import argparse
import os
from pathlib import Path
import sys
from dotenv import dotenv_values


def main():
    """Load the selected private configuration and replace this process with Gunicorn."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("api", "identity"))
    parser.add_argument("--environment", type=Path, required=True)
    args = parser.parse_args()
    if args.environment.stat().st_mode & 0o077:
        parser.error("Environment must be private (chmod 600).")
    settings = dotenv_values(args.environment)
    if settings.get("OLDAP_BACKEND") != "jena":
        parser.error("Native Jena services require OLDAP_BACKEND=jena.")
    os.environ.update({key: value for key, value in settings.items() if value is not None})
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    root = Path(__file__).resolve().parent
    os.chdir(root)
    if args.role == "identity":
        target, port = "jena_identity:create_app()", "8001"
        extra = ["--pythonpath", str(root.parent / "oldap-setup/scripts")]
    else:
        target, port, extra = "oldap_api.wsgi:app", settings.get("OLDAP_API_PORT", "8000"), []
    os.execv(sys.executable, [sys.executable, "-m", "gunicorn", target,
        "--bind", "127.0.0.1:" + port, "--workers", "1", "--threads", "4",
        "--timeout", "120", "--graceful-timeout", "120", *extra])


if __name__ == "__main__":
    main()
