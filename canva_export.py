#!/usr/bin/env python3
"""
canva_export.py — refresh the Canva token, PERSIST the rotated refresh token,
then export every page of the design as a PNG into ./assets/.

This is the engine the GitHub Action runs. The single most important thing it
does is survive Canva's refresh-token rotation: every call to /oauth/token
invalidates the old refresh token and issues a new one. If the new one isn't
saved, the NEXT run dies with invalid_grant. So we persist it FIRST, before any
export work, and log the rotation loudly.

Persistence targets:
  - In GitHub Actions (GITHUB_ACTIONS=true): write it back to the repo secret
    CANVA_REFRESH_TOKEN via `gh secret set` (needs GH_PAT with secrets write).
  - Locally: rewrite canva_tokens.json (and .env if present).

Env:
  CANVA_CLIENT_ID, CANVA_CLIENT_SECRET   (required)
  CANVA_REFRESH_TOKEN                     (required; falls back to canva_tokens.json locally)
  CANVA_DESIGN_ID                         (required)
  GH_PAT, GITHUB_REPOSITORY               (CI only, for secret write-back)
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.canva.com/rest/v1"
TOKEN_URL = f"{API}/oauth/token"
ROOT = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(ROOT, "canva_tokens.json")
ASSETS_DIR = os.path.join(ROOT, "assets")

CLIENT_ID = os.environ.get("CANVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET")
DESIGN_ID = os.environ.get("CANVA_DESIGN_ID")
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def die(msg):
    sys.exit(f"ERROR: {msg}")


def mask(secret):
    """Tell Actions to redact this value from all logs."""
    if IN_CI and secret:
        print(f"::add-mask::{secret}")


def load_refresh_token():
    tok = os.environ.get("CANVA_REFRESH_TOKEN")
    if tok:
        return tok
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE) as f:
            tok = json.load(f).get("refresh_token")
            if tok:
                return tok
    die("no refresh token in CANVA_REFRESH_TOKEN or canva_tokens.json")


def persist_refresh_token(new_token):
    """Save the rotated refresh token so the next run can authenticate."""
    mask(new_token)
    if IN_CI:
        pat = os.environ.get("GH_PAT")
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not pat or not repo:
            die("in CI but GH_PAT / GITHUB_REPOSITORY missing — cannot write back "
                "the rotated refresh token; next run would fail with invalid_grant.")
        env = {**os.environ, "GH_TOKEN": pat}
        try:
            subprocess.run(
                ["gh", "secret", "set", "CANVA_REFRESH_TOKEN",
                 "--repo", repo, "--body", new_token],
                check=True, env=env, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as e:
            die(f"gh secret set failed: {e.stderr.strip()}")
        print(f"[rotate] refresh token rotated and written to secret "
              f"CANVA_REFRESH_TOKEN on {repo}.")
    else:
        with open(TOKENS_FILE, "w") as f:
            json.dump({"refresh_token": new_token}, f, indent=2)
        print(f"[rotate] refresh token rotated and saved to {TOKENS_FILE}.")


def refresh_access_token():
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": load_refresh_token(),
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req) as r:
            tokens = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        if "invalid_grant" in detail:
            die("refresh token is stale/expired (invalid_grant). Re-run "
                "canva_oauth_setup.py to mint a fresh one and update the secret.")
        die(f"token refresh failed (HTTP {e.code}): {detail}")
    # PERSIST FIRST — before any export work can fail and strand us.
    persist_refresh_token(tokens["refresh_token"])
    print("[auth] access token acquired.")
    return tokens["access_token"]


def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def api_post(path, token, payload):
    req = urllib.request.Request(
        f"{API}{path}", data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def unwrap(obj, *keys):
    for container in (obj, obj.get("job", {}), obj.get("design", {})):
        if isinstance(container, dict):
            for k in keys:
                if k in container:
                    return container[k]
    return None


def export_all_pages(token):
    """Export the whole design as PNG; return the list of page image URLs in order."""
    job = api_post("/exports", token,
                   {"design_id": DESIGN_ID, "format": {"type": "png"}})
    job_id = unwrap(job, "id")
    print(f"[export] job {job_id} started; polling...")
    for _ in range(60):  # up to ~2 min
        time.sleep(2)
        res = api_get(f"/exports/{job_id}", token)
        status = unwrap(res, "status")
        if status == "success":
            urls = unwrap(res, "urls") or []
            print(f"[export] success — {len(urls)} page(s).")
            return urls
        if status == "failed":
            die(f"export job failed: {json.dumps(res)}")
    die("export did not finish in time")


def download(urls):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    for i, url in enumerate(urls, start=1):
        out = os.path.join(ASSETS_DIR, f"page-{i}.png")
        urllib.request.urlretrieve(url, out)
        kb = round(os.path.getsize(out) / 1024, 1)
        print(f"[download] assets/page-{i}.png ({kb} KB)")


def main():
    if not (CLIENT_ID and CLIENT_SECRET):
        die("set CANVA_CLIENT_ID and CANVA_CLIENT_SECRET")
    if not DESIGN_ID:
        die("set CANVA_DESIGN_ID")
    token = refresh_access_token()
    urls = export_all_pages(token)
    download(urls)
    print("[done] all pages exported to assets/.")


if __name__ == "__main__":
    main()
