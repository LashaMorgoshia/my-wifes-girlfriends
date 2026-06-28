"""
ვიდეოების გადმოწერა საიტიდან: https://tv.formula.ge/tvseries/show/1/main
(სერიალი "ჩემი ცოლის დაქალები")

გამოყენება:
    python download_formula.py                 # ყველა სეზონი, უმაღლესი ხარისხი
    python download_formula.py --season 1      # მხოლოდ სეზონი #1
    python download_formula.py --season 1 2 3  # კონკრეტული სეზონები
    python download_formula.py --quality 720p  # კონკრეტული ხარისხი (1080p|720p|360p)
    python download_formula.py --series 1      # სხვა სერიალის ID

ფაილები ინახება დირექტორიაში: ./სეზონი <N>/სერია <N>.mp4
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

API_BASE = "https://mw-api.formula.ge/formula/api/tvseries"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://tv.formula.ge/",
    "Origin": "https://tv.formula.ge",
}

QUALITY_ORDER = ["1080p", "720p", "360p"]


def sanitize(name: str) -> str:
    """Windows-უსაფრთხო ფაილის სახელი."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    return name or "untitled"


def fetch_seasons(series_id: int) -> list[dict]:
    r = requests.get(f"{API_BASE}/{series_id}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_episodes(season_internal_id: int) -> list[dict]:
    r = requests.get(
        f"{API_BASE}/episodes/{season_internal_id}", headers=HEADERS, timeout=30
    )
    r.raise_for_status()
    return r.json()


def pick_source(sources: list[dict], preferred: Optional[str]) -> Optional[tuple[str, str]]:
    if not sources:
        return None
    by_key = {s["key"]: s["value"] for s in sources if s.get("value")}
    if preferred and preferred in by_key:
        return preferred, by_key[preferred]
    for q in QUALITY_ORDER:
        if q in by_key:
            return q, by_key[q]
    # fallback — პირველი ხელმისაწვდომი
    first = next(iter(by_key.items()), None)
    return first


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        # შევამოწმოთ Content-Length თუ ფაილი სრულია
        try:
            head = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=True)
            total = int(head.headers.get("Content-Length", "0"))
            if total and dest.stat().st_size >= total:
                print(f"  [skip] უკვე გადმოწერილია: {dest.name}")
                return True
        except requests.RequestException:
            pass

    tmp = dest.with_suffix(dest.suffix + ".part")
    resume_from = tmp.stat().st_size if tmp.exists() else 0

    for attempt in range(1, retries + 1):
        try:
            headers = dict(HEADERS)
            if resume_from:
                headers["Range"] = f"bytes={resume_from}-"
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                if r.status_code in (200, 206):
                    total = int(r.headers.get("Content-Length", "0")) + resume_from
                    mode = "ab" if resume_from and r.status_code == 206 else "wb"
                    if mode == "wb":
                        resume_from = 0
                    downloaded = resume_from
                    last_print = time.time()
                    with open(tmp, mode) as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded += len(chunk)
                            now = time.time()
                            if now - last_print > 0.5:
                                last_print = now
                                if total:
                                    pct = downloaded * 100 / total
                                    sys.stdout.write(
                                        f"\r  ↓ {dest.name}  {downloaded/1024/1024:7.1f}/"
                                        f"{total/1024/1024:.1f} MB  ({pct:5.1f}%)"
                                    )
                                else:
                                    sys.stdout.write(
                                        f"\r  ↓ {dest.name}  {downloaded/1024/1024:7.1f} MB"
                                    )
                                sys.stdout.flush()
                    sys.stdout.write("\n")
                    tmp.rename(dest)
                    return True
                else:
                    print(f"  HTTP {r.status_code} — სცადე თავიდან ({attempt}/{retries})")
        except requests.RequestException as e:
            print(f"  შეცდომა: {e} — სცადე თავიდან ({attempt}/{retries})")
            time.sleep(2 * attempt)
            resume_from = tmp.stat().st_size if tmp.exists() else 0
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Formula TV series downloader")
    parser.add_argument("--series", type=int, default=1, help="სერიალის ID (default: 1)")
    parser.add_argument(
        "--season",
        type=int,
        nargs="*",
        help="სეზონის ნომერი (seasonId, მაგ. 1, 2, ... 18). თუ არ მიეთითება — ყველა.",
    )
    parser.add_argument(
        "--quality",
        choices=QUALITY_ORDER,
        default=None,
        help="სასურველი ხარისხი (default: უმაღლესი ხელმისაწვდომი)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.cwd(),
        help="გადმოწერის ძირითადი დირექტორია (default: მიმდინარე)",
    )
    args = parser.parse_args()

    print(f"სერიალის ID = {args.series}")
    seasons = fetch_seasons(args.series)
    print(f"მოიძებნა {len(seasons)} სეზონი")

    # სეზონის seasonId-ით ფილტრი
    if args.season:
        wanted = {f"{n:02d}" for n in args.season} | {str(n) for n in args.season}
        seasons = [s for s in seasons if s.get("seasonId") in wanted]
        if not seasons:
            print("მითითებული სეზონები ვერ მოიძებნა.", file=sys.stderr)
            return 1

    args.out.mkdir(parents=True, exist_ok=True)

    total_ok = 0
    total_fail = 0

    for season in seasons:
        season_label = (season.get("seasonId") or "").lstrip("0") or season.get("seasonId")
        season_dir = args.out / sanitize(f"სეზონი {season_label}")
        season_dir.mkdir(exist_ok=True)
        print(f"\n=== სეზონი {season_label} (internal id={season['id']}) ===")

        episodes = fetch_episodes(season["id"])
        # დავალაგოთ ზრდადობით
        episodes.sort(key=lambda e: int(e.get("orderId") or e.get("episodeId") or 0))

        for ep in episodes:
            ep_num = ep.get("orderId") or ep.get("episodeId")
            sources = ep.get("sourceList") or []
            picked = pick_source(sources, args.quality)
            if not picked:
                # fallback to videoSRC
                fallback = ep.get("videoSRC") or ep.get("videoFhdSrc") or ep.get(
                    "videoHdSrc"
                ) or ep.get("videoSdSrc")
                if fallback:
                    picked = ("?", fallback)
            if not picked:
                print(f"  [warn] სერია {ep_num}: ვიდეო წყარო არ მოიძებნა")
                total_fail += 1
                continue
            quality, url = picked
            filename = sanitize(f"სერია {ep_num} [{quality}].mp4")
            dest = season_dir / filename
            print(f"  • სერია {ep_num}  ({quality})")
            ok = download_file(url, dest)
            if ok:
                total_ok += 1
            else:
                total_fail += 1

    print(f"\nდასრულდა. წარმატებული: {total_ok}, ჩავარდნილი: {total_fail}")
    return 0 if total_fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
