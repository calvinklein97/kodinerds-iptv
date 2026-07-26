#!/usr/bin/env python3
"""
Erzeugt ein Dummy-XMLTV-EPG fuer die Radio-Playlist.
Jeder Sender bekommt ganztaegig 4h-Bloecke, deren Titel einfach nur
der Sendername ist. Matching erfolgt ueber tvg-name (als channel id
UND display-name), da die Playlist kein tvg-id fuehrt.

Aufruf:
    python generate_radio_epg.py

Erwartet die Playlist unter iptv/clean/clean_radio_de.m3u (relativ zum
Repo-Root) und schreibt das EPG nach epg/radio_epg.xml.
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    print("zoneinfo nicht verfuegbar - Python >= 3.9 erforderlich", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYLIST_PATH = REPO_ROOT / "iptv" / "clean" / "clean_radio_de.m3u"
OUTPUT_PATH = REPO_ROOT / "epg" / "radio_epg.xml"

TZ = ZoneInfo("Europe/Berlin")
BLOCK_HOURS = 4
DAYS_AHEAD = 3  # heute + N Tage puffer, damit Player immer genug EPG-Daten sehen

TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')


def extract_channel_names(playlist_text: str) -> list[str]:
    """Liest alle tvg-name Werte in Reihenfolge, dedupliziert dabei."""
    seen = set()
    ordered_names = []
    for line in playlist_text.splitlines():
        if not line.startswith("#EXTINF"):
            continue
        match = TVG_NAME_RE.search(line)
        if not match:
            continue
        name = match.group(1).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered_names.append(name)
    return ordered_names


def build_xmltv(channel_names: list[str]) -> str:
    now_local = datetime.now(TZ)
    start_of_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_of_today + timedelta(days=DAYS_AHEAD)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<!DOCTYPE tv SYSTEM "xmltv.dtd">')
    lines.append('<tv generator-info-name="calvinklein97-radio-dummy-epg">')

    for name in channel_names:
        escaped_name = escape(name)
        lines.append(f'  <channel id="{escaped_name}">')
        lines.append(f'    <display-name lang="de">{escaped_name}</display-name>')
        lines.append("  </channel>")

    for name in channel_names:
        escaped_name = escape(name)
        block_start = start_of_today
        while block_start < end_time:
            block_stop = block_start + timedelta(hours=BLOCK_HOURS)
            start_str = block_start.strftime("%Y%m%d%H%M%S %z")
            stop_str = block_stop.strftime("%Y%m%d%H%M%S %z")
            lines.append(
                f'  <programme start="{start_str}" stop="{stop_str}" channel="{escaped_name}">'
            )
            lines.append(f'    <title lang="de">{escaped_name}</title>')
            lines.append("  </programme>")
            block_start = block_stop

    lines.append("</tv>")
    return "\n".join(lines) + "\n"


def main() -> None:
    if not PLAYLIST_PATH.exists():
        print(f"Playlist nicht gefunden: {PLAYLIST_PATH}", file=sys.stderr)
        sys.exit(1)

    playlist_text = PLAYLIST_PATH.read_text(encoding="utf-8")
    channel_names = extract_channel_names(playlist_text)

    if not channel_names:
        print("Keine tvg-name Eintraege gefunden - Abbruch.", file=sys.stderr)
        sys.exit(1)

    xmltv = build_xmltv(channel_names)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(xmltv, encoding="utf-8")
    print(f"EPG geschrieben: {OUTPUT_PATH} ({len(channel_names)} Sender)")


if __name__ == "__main__":
    main()
