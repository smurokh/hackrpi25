#!/usr/bin/env python3
"""
launcher.py

Run interactive pygame games described in games.json without assuming a virtualenv.

This version captures stdout from each interactive game process and looks for
a small JSON result object printed by the game. If any game reports action == "skipped",
the launcher sets `all_levels_completed` to False. The variable starts True.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
import os

ROOT = Path(__file__).resolve().parent


def load_manifest(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resource_base() -> Path:
    """
    Resolve base path for resource access (works with PyInstaller if used).
    Games can call the provided utils.resource_path.resource_path helper which
    uses a similar mechanism.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return ROOT


def run_interactive(entry: Path, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """
    Run an interactive pygame script as a subprocess and wait for it to exit.
    Capture stdout/stderr so we can parse a small JSON result printed at exit.
    Returns (returncode, stdout, stderr).
    """
    print(f"Starting interactive game: {entry}")
    # Capture stdout/stderr; it's safe for interactive windows to open while we capture output.
    proc = subprocess.Popen(
        [sys.executable, str(entry)],
        cwd=str(entry.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = proc.communicate()  # wait for process to exit
    rc = proc.returncode
    if err:
        print(f"--- stderr from {entry.name} ---\n{err}")
    return rc, (out or "").strip(), (err or "").strip()


def os_environ_safe() -> Dict[str, str]:
    """
    Return a sanitized copy of os.environ with str keys/values. This is used
    to pass environment variables into subprocesses safely.
    """
    env = {}
    for k, v in os.environ.items():
        env[str(k)] = str(v)
    return env


def run_game_cfg(cfg: dict, override_mode: Optional[str] = None) -> Optional[str]:
    """
    Run a single game config. For this repository we treat everything as interactive.
    Returns the parsed action string from the game's JSON result if available,
    otherwise None.
    """
    name = cfg.get("name")
    entry = cfg.get("entry")
    mode = override_mode or cfg.get("mode", "interactive")

    print("=" * 60)
    print(f"Run: {name}  mode={mode}  entry={entry}")

    entry_path = Path(entry)
    if not entry_path.is_absolute():
        entry_path = (ROOT / entry_path).resolve()

    if not entry_path.exists():
        print("Entry path not found:", entry_path)
        return None

    # Allow games to find resources; set GAME_BASE in env
    env = os_environ_safe()
    env["GAME_BASE"] = str(resource_base())

    try:
        if mode == "interactive":
            rc, stdout, stderr = run_interactive(entry_path, env=env)
            # Try to parse JSON from stdout (games are expected to print a small JSON result)
            if stdout:
                try:
                    parsed = json.loads(stdout.strip())
                    action = parsed.get("action")
                    print(f"Game {name} reported action: {action!r}")
                    return action
                except Exception:
                    # not JSON; ignore but show a snippet
                    print(f"Game {name} printed (non-JSON): {stdout[:200]!r}")
                    return None
            else:
                return None
        else:
            # treat other modes as interactive for now
            rc, stdout, stderr = run_interactive(entry_path, env=env)
            if stdout:
                try:
                    parsed = json.loads(stdout.strip())
                    return parsed.get("action")
                except Exception:
                    return None
    except Exception as e:
        print("Error running game:", e)
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description="Run interactive pygame games (no venv required).")
    p.add_argument("--manifest", "-m", default=str(ROOT / "games.json"))
    p.add_argument("--game", "-g", help="Run single game by name")
    p.add_argument("--loop", action="store_true", help="Run all games repeatedly (dev loop)")
    p.add_argument("--mode", help="Override mode (unused for interactive-only runs)")
    args = p.parse_args(argv)

    try:
        games = load_manifest(Path(args.manifest))
    except Exception as e:
        print("Failed to load manifest:", e)
        return 2

    if args.game:
        games = [g for g in games if g.get("name") == args.game]
        if not games:
            print("No such game:", args.game)
            return 3

    # This variable starts True and becomes False if any level is skipped.
    all_levels_completed = True

    def one_pass():
        nonlocal all_levels_completed
        for g in games:
            action = run_game_cfg(g, override_mode=args.mode)
            if action == "skipped":
                all_levels_completed = False

    if args.loop:
        print("Starting dev loop (press CTRL+C to stop).")
        try:
            while True:
                one_pass()
                print(f"All levels completed so far: {all_levels_completed}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Loop stopped by user.")
    else:
        one_pass()
        print("=" * 60)
        print(f"All levels completed: {all_levels_completed}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))