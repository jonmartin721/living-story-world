from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_VENV_PYTHONS = (
    ROOT / ".venv" / "Scripts" / "python.exe",
    ROOT / ".venv" / "bin" / "python",
)


def find_repo_python() -> Path | None:
    for candidate in LOCAL_VENV_PYTHONS:
        if candidate.exists():
            return candidate
    return None


def resolve_npm() -> str:
    if os.name == "nt":
        return shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    return shutil.which("npm") or "npm"


def ensure_repo_python() -> int | None:
    repo_python = find_repo_python()
    if repo_python is None:
        return None

    current_python = Path(sys.executable).resolve()
    if current_python == repo_python.resolve():
        return None

    print(f"Using repo virtualenv: {repo_python}", flush=True)
    return subprocess.run(
        [str(repo_python), str(Path(__file__)), "--using-repo-venv", *sys.argv[1:]],
        cwd=ROOT,
        check=False,
    ).returncode


def run_step(title: str, command: list[str]) -> None:
    print(f"\n==> {title}", flush=True)
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    if "--using-repo-venv" not in sys.argv:
        delegated_exit_code = ensure_repo_python()
        if delegated_exit_code is not None:
            return delegated_exit_code

    npm = resolve_npm()
    run_step("Backend tests", [sys.executable, "-m", "pytest"])
    run_step("Frontend tests", [npm, "test", "--prefix", "frontend", "--", "--run"])
    run_step("Frontend build", [npm, "run", "build", "--prefix", "frontend"])
    print("\nVerification complete.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
