#!/usr/bin/env python3
"""
Download Teenieping images into ./images/.

Run from the folder containing index.html:

    python3 get-images.py

The script reads the PINGS data from index.html and makes sure every character
has a verified local image at images/Name.webp.

Two passes:

1. For entries that list an explicit `img` URL, fetch it directly and save the
   verified image response as images/Name.webp.

2. For entries that still have no local image (the wiki "Special:Redirect"
   links reject automated downloads), ask the fandom API for the page's
   original image via prop=pageimages, download that, and convert it to WebP
   with `sips` so it matches the other files.

Any image the script adds is written into IMAGE_MANIFEST in index.html so the
app picks it up automatically.
"""
import imghdr
import io
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
IMAGES = ROOT / "images"
API = "https://catchteenieping.fandom.com/api.php"
MAX_WIDTH = 400  # cap width so new files stay in line with the existing ones
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


def load_manifest():
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"const IMAGE_MANIFEST = Object\.freeze\((\{[\s\S]*?\})\);", html)
    if not match:
        raise SystemExit("Could not find IMAGE_MANIFEST in index.html")
    data = re.sub(r",\s*([}\]])", r"\1", match.group(1))
    return json.loads(data)


def write_manifest(manifest):
    """Rewrite IMAGE_MANIFEST in index.html, keys sorted alphabetically."""
    html = INDEX.read_text(encoding="utf-8")
    lines = [
        f'  "{name}": "{manifest[name]}",' for name in sorted(manifest)
    ]
    block = "const IMAGE_MANIFEST = Object.freeze({\n" + "\n".join(lines) + "\n});"
    new_html, count = re.subn(
        r"const IMAGE_MANIFEST = Object\.freeze\(\{[\s\S]*?\}\);",
        lambda _m: block,
        html,
        count=1,
    )
    if count != 1:
        raise SystemExit("Could not rewrite IMAGE_MANIFEST in index.html")
    INDEX.write_text(new_html, encoding="utf-8")


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def to_webp(blob, target):
    """Convert an image blob to WebP at `target`, capping width at MAX_WIDTH."""
    kind = imghdr.what(None, blob)
    if kind not in {"png", "jpeg", "webp"} or len(blob) < 2000:
        raise ValueError(f"not a usable image: {kind}, {len(blob)} bytes")
    image = Image.open(io.BytesIO(blob))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    if image.width > MAX_WIDTH:
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.LANCZOS)
    image.save(target, "WEBP", quality=80, method=6)
    if not target.exists() or target.stat().st_size < 2000:
        raise ValueError("Pillow produced no usable WebP")


def api_originals(names):
    """Map {requested name -> original image source URL} via prop=pageimages."""
    sources = {}
    for i in range(0, len(names), 50):
        batch = names[i:i + 50]
        params = urllib.parse.urlencode({
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "piprop": "original",
            "redirects": "1",
            "titles": "|".join(batch),
        })
        payload = json.loads(fetch(f"{API}?{params}").decode("utf-8"))
        query = payload.get("query", {})

        # Resolve normalized titles and redirects back to the requested names.
        alias = {}
        for entry in query.get("normalized", []):
            alias[entry["to"]] = entry["from"]
        for entry in query.get("redirects", []):
            alias[entry["to"]] = alias.get(entry["from"], entry["from"])

        for page in query.get("pages", {}).values():
            original = page.get("original")
            if not original:
                continue
            requested = alias.get(page["title"], page["title"])
            sources[requested] = original["source"]
        time.sleep(0.2)
    return sources


def main():
    IMAGES.mkdir(exist_ok=True)
    pings = load_pings()
    manifest = load_manifest()
    downloaded = skipped = failed = 0

    # Pass 1: entries with an explicit image URL and no local file yet.
    for ping in pings:
        name = ping["n"]
        target = IMAGES / f"{name}.webp"
        if target.exists() and target.stat().st_size > 2000:
            manifest[name] = f"images/{name}.webp"
            skipped += 1
            continue

        url = ping.get("img", "")
        if not url or "Special:Redirect" in url:
            continue  # handled by the API pass below

        try:
            to_webp(fetch(url), target)
            manifest[name] = f"images/{name}.webp"
            print(f"got {name}")
            downloaded += 1
            time.sleep(0.15)
        except Exception as exc:
            print(f"failed {name}: {exc}")
            failed += 1

    # Pass 2: anything still missing a local image, via the fandom API.
    missing = [
        p["n"] for p in pings
        if not (IMAGES / f"{p['n']}.webp").exists()
        or (IMAGES / f"{p['n']}.webp").stat().st_size <= 2000
    ]
    if missing:
        print(f"Querying fandom API for {len(missing)} missing image(s)...")
        sources = api_originals(missing)
        for name in missing:
            source = sources.get(name)
            if not source:
                print(f"failed {name}: no original image from API")
                failed += 1
                continue
            try:
                to_webp(fetch(source), IMAGES / f"{name}.webp")
                manifest[name] = f"images/{name}.webp"
                print(f"got {name} (via API)")
                downloaded += 1
                time.sleep(0.15)
            except Exception as exc:
                print(f"failed {name}: {exc}")
                failed += 1

    write_manifest(manifest)
    print(f"Done. Downloaded {downloaded}. Already had {skipped}. Failed {failed}.")
    print(f"IMAGE_MANIFEST now lists {len(manifest)} images.")


if __name__ == "__main__":
    main()
