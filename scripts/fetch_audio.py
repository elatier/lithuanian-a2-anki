#!/usr/bin/env python3
"""fetch_audio.py — download the deck's recorded audio instead of re-synthesising it.

Synthesising the 6,372 clips from scratch takes about five hours at the rate
LIEPA allows. The clips are published as a release asset instead; this
downloads that archive, checks its SHA-256 and unpacks it into media_tmp/.
Clips already in media_tmp/ are left alone.

    python3 scripts/fetch_audio.py
    python3 scripts/fetch_audio.py --zip lietuviu_A2_audio.zip   # already downloaded

Afterwards, scripts/resume_audio.py records only what the archive lacks:
clips for new words, and clips whose text has changed since.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import paths

URL = ("https://github.com/elatier/lithuanian-a2-anki/releases/download/"
       "v1.0.0/lietuviu_A2_audio.zip")
SHA256 = "8f7eadd1ac818bb99b4d097acc0f02824d5c5aff170b51961d8252f269e5c0d6"
MANIFEST = ".text_manifest.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    print(f"downloading {url}", flush=True)
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done >> 20} / {total >> 20} MB", end="", flush=True)
    print()


def unpack(zpath):
    paths.MEDIA.mkdir(exist_ok=True)
    added = kept = 0
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if name == MANIFEST:
                continue
            if Path(name).name != name or not name.endswith(".mp3"):
                sys.exit(f"unexpected entry in archive: {name!r}")
            dest = paths.MEDIA / name
            if dest.exists() and dest.stat().st_size > 0:
                kept += 1
                continue
            with z.open(name) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            added += 1
        # merge the manifest: local entries win, they describe local clips
        theirs = json.loads(z.read(MANIFEST).decode("utf-8"))
    local = paths.MEDIA / MANIFEST
    ours = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
    local.write_text(json.dumps({**theirs, **ours}, ensure_ascii=False, indent=0),
                     encoding="utf-8")
    print(f"{added} clip(s) added to {paths.MEDIA.name}/, "
          f"{kept} already there")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", help="use a local copy of the archive")
    ap.add_argument("--url", default=URL)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(args.zip) if args.zip else Path(tmp) / "audio.zip"
        if not args.zip:
            download(args.url, zpath)
        got = sha256(zpath)
        if args.url == URL and got != SHA256:
            sys.exit(f"checksum mismatch: expected {SHA256}, got {got}")
        unpack(zpath)


if __name__ == "__main__":
    main()
