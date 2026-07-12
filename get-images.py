#!/usr/bin/env python3
"""
Download Teenieping images into ./images/.

Run from the folder containing index.html:

    python3 get-images.py

The script reads the PINGS data from index.html, tries each entry's explicit
image URL, and saves verified image responses as images/Name.webp. Some wiki
redirect URLs may reject automated downloads; those characters should keep
their emoji badge until a verified local image is added by hand.
"""
import imghdr
import json
import pathlib
import re
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
IMAGES = ROOT / "images"
HEADERS = {
    "User-Agent": "Mozilla/5.0 TeeniepingCatcher/1.0",
    "Referer": "https://catchteenieping.fandom.com/",
}


def load_pings():
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"const PINGS = (\[\n[\s\S]*?\n\]);", html)
    if not match:
        raise SystemExit("Could not find PINGS data in index.html")
    data = re.sub(r"/\*[\s\S]*?\*/", "", match.group(1))
    data = re.sub(r"([\{,])\s*([A-Za-z_]\w*)\s*:", r'\1"\2":', data)
    data = re.sub(r",\s*([}\]])", r"\1", data)
    return json.loads(data)


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:
        return response.read()


def main():
    IMAGES.mkdir(exist_ok=True)
    pings = load_pings()
    downloaded = skipped = failed = 0

    for ping in pings:
        name = ping["n"]
        target = IMAGES / f"{name}.webp"
        if target.exists() and target.stat().st_size > 2000:
            skipped += 1
            continue

        url = ping.get("img")
        if not url:
            print(f"missing {name}: no image URL")
            failed += 1
            continue

        try:
            blob = fetch(url)
            kind = imghdr.what(None, blob)
            if kind not in {"png", "jpeg", "webp"} or len(blob) < 2000:
                raise ValueError(f"not a usable image: {kind}, {len(blob)} bytes")
            target.write_bytes(blob)
            print(f"got {name}")
            downloaded += 1
            time.sleep(0.15)
        except Exception as exc:
            print(f"failed {name}: {exc}")
            failed += 1

    print(f"Done. Downloaded {downloaded}. Already had {skipped}. Failed {failed}.")
    print("After adding new files, update IMAGE_MANIFEST in index.html.")


if __name__ == "__main__":
    main()
