"""CloakBrowser login helper.

ChatlyAI's sign-in is behind Cloudflare Turnstile, which blocks ordinary
automated browsers. CloakBrowser (a stealth Chromium) passes the challenge.
We log in once, click the Turnstile checkbox, and persist the resulting
cookies as a Playwright ``storage_state`` JSON that the API client reuses.

Requires a display (set ``DISPLAY``, e.g. ``:0``). Headless is detectable and
usually fails the challenge, so we run headed by default.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from . import config
from .accounts import AccountStore


def _turnstile_token_len(page) -> int:
    try:
        return page.evaluate(
            "()=>{const el=document.querySelector('input[name=\"cf-turnstile-response\"],"
            "textarea[name=\"cf-turnstile-response\"]');return el?(el.value||'').length:-1;}"
        )
    except Exception:
        return -2


def login(
    email: str,
    password: str,
    name: str = "account1",
    headless: bool = False,
    keep_open_sec: int = 0,
) -> Path:
    """Log in and save storage_state to ``profiles/<name>_state.json``.

    Returns the path to the saved state file. Registers the account too.
    """
    from cloakbrowser import launch_persistent_context

    user_dir = config.PROFILES_DIR / f"{name}_userdir"
    state_path = config.PROFILES_DIR / f"{name}_state.json"
    user_dir.mkdir(parents=True, exist_ok=True)

    ctx = launch_persistent_context(
        str(user_dir), headless=headless, humanize=True,
        viewport={"width": 1280, "height": 900},
    )
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(config.SIGN_IN_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        page.fill('input[name="email"]', email)
        time.sleep(1)
        page.click('form button:has-text("Continue")', timeout=8000)
        page.wait_for_selector('input[name="password"]', timeout=20000)
        page.fill('input[name="password"]', password)
        time.sleep(1)

        # Solve Turnstile: click the checkbox (locate the cloudflare widget bbox).
        box = None
        for sel in (
            'iframe[src*="challenges.cloudflare.com"]',
            'div.cf-turnstile',
            'div[class*="turnstile"]',
        ):
            el = page.query_selector(sel)
            if el:
                try:
                    box = el.bounding_box()
                    if box:
                        break
                except Exception:
                    pass
        if box:
            page.mouse.move(box["x"] - 60, box["y"] + box["height"] / 2 - 40)
            time.sleep(0.3)
            page.mouse.click(box["x"] + 28, box["y"] + box["height"] / 2)
        else:
            page.mouse.click(450, 462)  # fallback to observed checkbox position

        for _ in range(40):
            time.sleep(2)
            if _turnstile_token_len(page) > 5:
                break

        page.click('form button[type="submit"]', timeout=8000)

        ok = False
        for _ in range(45):
            time.sleep(2)
            if "chatlyai.app" in page.url and "/auth" not in page.url:
                ok = True
                break
        if not ok:
            raise RuntimeError(
                f"Login did not reach chatlyai.app (still at {page.url}). "
                "Turnstile may have failed or credentials are wrong."
            )

        ctx.storage_state(path=str(state_path))
        AccountStore().register(name, state_path, label=email)
        if keep_open_sec:
            time.sleep(keep_open_sec)
        return state_path
    finally:
        try:
            ctx.close()
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    import os

    ap = argparse.ArgumentParser(description="Log in to ChatlyAI via CloakBrowser")
    ap.add_argument("--name", default="account1")
    ap.add_argument("--email", default=os.environ.get("CHATLYAI_EMAIL"))
    ap.add_argument("--password", default=os.environ.get("CHATLYAI_PASSWORD"))
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    if not args.email or not args.password:
        raise SystemExit("Provide --email/--password or set CHATLYAI_EMAIL/PASSWORD")
    p = login(args.email, args.password, name=args.name, headless=args.headless)
    print("saved state ->", p)
