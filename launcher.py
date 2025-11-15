#!/usr/bin/env python3
"""
launcher.py

Runs interactive pygame games described in games.json without a venv.

Fixes & robustness:
- Launch child Python with -u (unbuffered) and set PYTHONUNBUFFERED in env so prints from GUI games
  are captured immediately when they exit.
- When parsing child stdout, scan lines and try json.loads on each non-empty line until one parses.
  This tolerates games that print other debug text before/after the JSON.
- Preserve previous behavior: store a captured player_name and set all_levels_completed False when
  any game's parsed action == "skipped".
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Tuple, Any, List
import os

ROOT = Path(__file__).resolve().parent


def load_manifest(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resource_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return ROOT


def run_interactive(entry: Path, extra_args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """
    Run an interactive pygame script as a subprocess and wait for it to exit.
    extra_args: list of extra command-line arguments to append after the entry script.
    Returns (returncode, stdout, stderr).

    Uses unbuffered python (-u) and sets PYTHONUNBUFFERED=1 in the child's env so printed JSON
    will reliably appear in stdout for the launcher to parse.
    """
    # Build command: use -u to force unbuffered stdout/stderr in child Python process
    cmd = [sys.executable, "-u", str(entry)]
    if extra_args:
        cmd += [str(a) for a in extra_args if a is not None]

    print("Starting interactive game:", " ".join(cmd))
    # Prepare env: copy current env then inject GAME_BASE and PYTHONUNBUFFERED to ensure child prints flush
    child_env = os.environ.copy()
    if env:
        # overlay sanitized env from launcher (env produced by os_environ_safe())
        child_env.update(env)
    # Ensure unbuffered output in child
    child_env["PYTHONUNBUFFERED"] = "1"

    # Start the process; capture stdout/stderr so we can parse the minimal JSON result the game prints.
    proc = subprocess.Popen(
        cmd,
        cwd=str(entry.parent),
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = proc.communicate()
    rc = proc.returncode
    if err:
        # print stderr for debugging
        print(f"--- stderr from {entry.name} ---\n{err}")
    return rc, (out or "").strip(), (err or "").strip()


def os_environ_safe() -> Dict[str, str]:
    env = {}
    for k, v in os.environ.items():
        env[str(k)] = str(v)
    return env


def _parse_first_json_from_stdout(stdout: str) -> Optional[dict]:
    """
    Scan stdout lines and try to parse a JSON object from the first line that parses.
    This is tolerant of extra log lines before/after the JSON.
    """
    if not stdout:
        return None
    # Try whole stdout first in case script prints only JSON
    s = stdout.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    # otherwise try line-by-line (skip empty lines)
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            return parsed
        except Exception:
            # continue scanning lines
            continue
    return None


def run_game_cfg(cfg: dict, extra_args: Optional[List[str]] = None, override_mode: Optional[str] = None) -> Optional[dict]:
    """
    Run a single game config. Treat as interactive by default.
    Returns parsed JSON dict from stdout if present, otherwise None.
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

    env = os_environ_safe()
    env["GAME_BASE"] = str(resource_base())

    try:
        rc, stdout, stderr = run_interactive(entry_path, extra_args=extra_args, env=env)
        if not stdout:
            return None
        parsed = _parse_first_json_from_stdout(stdout)
        if parsed is None:
            print(f"Game {name} printed (non-JSON or JSON not found). stdout snippet: {stdout[:200]!r}")
            return None
        print(f"Game {name} printed JSON: {parsed!r}")
        return parsed
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

    all_levels_completed = True
    current_player_name: Optional[str] = None

    def one_pass():
        nonlocal all_levels_completed, current_player_name
        for g in games:
            extra = [current_player_name] if current_player_name is not None else None
            parsed = run_game_cfg(g, extra_args=extra, override_mode=args.mode)
            if not parsed:
                continue
            action = parsed.get("action")
            if action == "skipped":
                all_levels_completed = False
            if "player_name" in parsed:
                current_player_name = parsed.get("player_name")

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
        print(f"Player name captured: {current_player_name!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))