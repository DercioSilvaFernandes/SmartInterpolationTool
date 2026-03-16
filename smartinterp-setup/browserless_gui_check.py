#!/usr/bin/env python3
"""Headless GUI validation for the SmartInterpolationTool webapp.

This script loads the real Flask UI in Chromium via Playwright, exercises the
main interpolation flow, and writes a screenshot artifact so the GUI can be
reviewed without an interactive browser session.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "smartinterp-setup" / "artifacts" / "browserless-gui-check.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the SmartInterpolationTool GUI without a browser window.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Webapp URL to test.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to the output screenshot artifact.",
    )
    parser.add_argument(
        "--launch-local-server",
        action="store_true",
        help="Start `python webapp/app.py` before running the GUI check.",
    )
    parser.add_argument(
        "--server-command",
        nargs="+",
        default=[
            sys.executable,
            "-c",
            "from webapp.app import app; app.run(host='127.0.0.1', port=5000, debug=False)",
        ],
        help="Command used with --launch-local-server.",
    )
    parser.add_argument("--robot-type", default="g1_29dof", help="Robot type to select in the UI.")
    parser.add_argument("--stand", default="stand_pose.csv", help="Stand motion to use.")
    parser.add_argument("--motion-a", default="motion_walk.csv", help="Primary motion clip.")
    parser.add_argument("--motion-b", default="motion_wave.csv", help="Optional second motion clip.")
    parser.add_argument("--steps", type=int, default=20, help="Interpolation step count.")
    parser.add_argument("--hold", type=int, default=5, help="Hold frame count.")
    parser.add_argument(
        "--easing",
        default="minimum_jerk",
        choices=["linear", "smoothstep", "minimum_jerk"],
        help="Interpolation easing mode.",
    )
    parser.add_argument("--timeout-ms", type=int, default=90000, help="Per-step timeout in milliseconds.")
    return parser.parse_args()


def wait_for_http_ready(url: str, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url} to become ready: {last_error}")


def start_server(command: list[str], base_url: str) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )
    try:
        wait_for_http_ready(base_url)
        return process
    except Exception:
        terminate_process(process)
        raise RuntimeError(f"Failed to start local server with command {command!r}")


def terminate_process(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def run_gui_check(args: argparse.Namespace) -> tuple[str, Path]:
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    server_process = start_server(args.server_command, args.base_url) if args.launch_local_server else None
    try:
        wait_for_http_ready(args.base_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1100})
            page.set_default_timeout(args.timeout_ms)

            console_errors: list[str] = []
            page_errors: list[str] = []
            dialogs: list[str] = []

            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("dialog", lambda dialog: dialogs.append(dialog.message) or dialog.dismiss())

            page.goto(args.base_url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightError:
                # The page pulls module assets from CDNs; network-idle is not a reliable
                # completion signal here, so rely on concrete UI readiness checks below.
                pass

            page.wait_for_selector("#canvasContainer canvas", state="attached")
            page.wait_for_function("document.querySelector('#standSelect')?.options.length > 1")

            current_robot_type = page.locator("#robotType").input_value()
            if current_robot_type != args.robot_type:
                page.select_option("#robotType", args.robot_type)
                page.wait_for_function(
                    "(expected) => document.querySelector('#robotType')?.value === expected",
                    args.robot_type,
                )
                page.wait_for_function("document.querySelector('#standSelect')?.options.length > 1")
            page.select_option("#standSelect", args.stand)
            page.select_option("#motionASelect", args.motion_a)
            if args.motion_b:
                page.select_option("#motionBSelect", args.motion_b)

            page.fill("#steps", str(args.steps))
            page.fill("#hold", str(args.hold))
            page.select_option("#easing", args.easing)
            page.click("#buildButton")

            page.wait_for_function("document.querySelector('#frameLabel')?.textContent.trim() !== '—'")
            page.wait_for_function("!document.querySelector('#downloadButton')?.disabled")
            page.click("#playPauseButton")
            page.wait_for_timeout(1500)
            page.screenshot(path=str(output_path))

            frame_label = page.locator("#frameLabel").inner_text().strip()
            play_label = page.locator("#playPauseButton").inner_text().strip()
            browser.close()

            failures = []
            if dialogs:
                failures.append(f"Dialog(s) raised by the app: {dialogs}")
            if page_errors:
                failures.append(f"Unhandled page error(s): {page_errors}")
            if console_errors:
                failures.append(f"Console error(s): {console_errors}")

            if failures:
                raise RuntimeError(" ; ".join(failures))

            return f"frame_label={frame_label}, play_button={play_label}", output_path
    except PlaywrightError as exc:
        raise RuntimeError(f"Playwright GUI check failed: {exc}") from exc
    finally:
        terminate_process(server_process)


def main() -> int:
    args = parse_args()
    summary, output_path = run_gui_check(args)
    print(f"GUI validation passed: {summary}")
    print(f"Screenshot written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
