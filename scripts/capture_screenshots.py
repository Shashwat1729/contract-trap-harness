#!/usr/bin/env python3
"""One-off script: drives the real live Streamlit dashboard with Playwright and saves
real screenshots to evidence/screenshots/. Not part of the reproduction pipeline --
run manually when refreshing submission visuals. Uses the system-installed Chrome
(channel="chrome") so no separate browser download is needed.
"""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8501"


def shot(page, name: str) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    print(f"saved {name}.png")


def click_tab(page, label: str) -> None:
    page.get_by_role("tab", name=label).click()
    page.wait_for_timeout(700)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(BASE, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)
        shot(page, "01_overview")

        click_tab(page, "📊 Metrics")
        shot(page, "02_metrics")

        click_tab(page, "🗂️ Trap Suite Explorer")
        shot(page, "03_trap_suite_explorer")

        click_tab(page, "🔬 Harness Monitor")
        page.wait_for_timeout(500)
        shot(page, "04_harness_monitor_empty")

        # Load a real fixture contract and run the real pipeline (regex-only, $0, no API key needed)
        try:
            page.get_by_role("button", name="Load Contract").click()
            page.wait_for_timeout(1200)
            shot(page, "05_harness_monitor_loaded")

            page.get_by_role("button", name="Run Harness (Baseline vs Advanced)").click()
            # Real pipeline run on a real contract -- give it real time to finish.
            page.wait_for_timeout(9000)
            shot(page, "06_harness_monitor_results")
        except Exception as exc:  # noqa: BLE001
            print(f"harness run interaction skipped: {exc}")

        click_tab(page, "🔁 Reproducibility")
        shot(page, "07_reproducibility")

        click_tab(page, "📈 Market")
        shot(page, "08_market")

        click_tab(page, "Tests")
        page.wait_for_timeout(500)
        shot(page, "09_tests")

        browser.close()


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"done in {time.time()-t0:.1f}s")
