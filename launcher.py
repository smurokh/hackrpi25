#!/usr/bin/env python3
"""
launcher.py

Runs interactive pygame games described in games.json without a venv.

Behavior:
- If a child prints JSON containing "player_name" the launcher stores it and
  immediately starts a session timer (time.time()).
- Subsequent games are launched with extra CLI args:
    [player_name, timer_start_timestamp]
  (timer_start_timestamp is only added after timer started).
- Each game should print a JSON object on exit (e.g. {"action":"finished", "elapsed_seconds": 12.345})
  The launcher will parse that JSON and update internal state (all_levels_completed and current player name).
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
    Run a child game as a subprocess and wait for it to exit.
    Use -u and PYTHONUNBUFFERED to ensure printed JSON appears in stdout reliably.
    Returns (returncode, stdout, stderr).
    """
    # Use -u for unbuffered child Python so printed JSON is flushed
    cmd = [sys.executable, "-u", str(entry)]
    if extra_args:
        cmd += [str(a) for a in extra_args if a is not None]
    print("Starting interactive game:", " ".join(cmd))

    # child env: copy current env and overlay launcher-provided env
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    # ensure unbuffered python in child
    child_env["PYTHONUNBUFFERED"] = "1"

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
        print(f"--- stderr from {entry.name} ---\n{err}")
    return rc, (out or "").strip(), (err or "").strip()


def os_environ_safe() -> Dict[str, str]:
    env = {}
    for k, v in os.environ.items():
        env[str(k)] = str(v)
    return env


def _parse_first_json_from_stdout(stdout: str) -> Optional[dict]:
    """
    Try parsing the entire stdout as JSON; if that fails, try line-by-line.
    Returns the first parsed JSON object found, or None.
    """
    if not stdout:
        return None
    s = stdout.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            return parsed
        except Exception:
            continue
    return None


def run_game_cfg(cfg: dict, extra_args: Optional[List[str]] = None, override_mode: Optional[str] = None) -> Optional[dict]:
    """
    Run a single game config. Returns parsed JSON dict from stdout (if any).
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
    timer_started = False
    timer_start_ts: Optional[float] = None

    def one_pass():
        nonlocal all_levels_completed, current_player_name, timer_started, timer_start_ts
        for g in games:
            # prepare extra args: first pass player_name then timer start ts (if started)
            extra: Optional[List[str]] = None
            if current_player_name is not None:
                extra = [current_player_name]
                if timer_started and timer_start_ts is not None:
                    extra.append(str(timer_start_ts))

            parsed = run_game_cfg(g, extra_args=extra, override_mode=args.mode)
            if not parsed:
                # no JSON printed / no parseable output
                continue

            # if the parsed JSON contains player_name, capture and start timer immediately
            if "player_name" in parsed:
                pname = parsed.get("player_name")
                # store name even if it's null
                current_player_name = pname
                if pname is not None and not timer_started:
                    timer_started = True
                    timer_start_ts = time.time()
                    print(f"Timer started at {timer_start_ts} for player {current_player_name!r}")

            # detect skip action
            action = parsed.get("action")
            if action == "skipped":
                all_levels_completed = False

            # read elapsed_seconds if returned and log it
            if "elapsed_seconds" in parsed:
                try:
                    elapsed = float(parsed.get("elapsed_seconds"))
                    print(f"Game {g.get('name')} reported elapsed_seconds: {elapsed:.3f}s")
                except Exception:
                    pass

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
        if timer_started:
            if timer_start_ts is not None:
                elapsed_total = time.time() - float(timer_start_ts)
                print(f"Total elapsed seconds since timer start: {elapsed_total:.3f}s")
            else:
                print("Timer was started but start timestamp is unavailable.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))