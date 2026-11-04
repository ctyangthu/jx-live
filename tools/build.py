"""Inline timetable, airports, map and audit results into src/app.html and write the site into dist/.

    python3 tools/build.py

dist/index.html     standalone page (open it directly in a browser, or host it anywhere)
dist/artifact.html  page body only, for hosts that add their own document skeleton
"""
import json
from schedule import ROOT, SEASON, parse

src = (ROOT / "src" / "app.html").read_text(encoding="utf-8")
segs = parse()
load = lambda name: json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
airports = load("airports.json")
airports.pop("_fields", None)
geo = load("map.json")
notes = load("audit-notes.json")
board = load("audit-airports.json")

audit = dict(tdx=load("audit-sources.json"), official=load("audit-official.json"), airports=board,
             added=notes["added"], notes=notes["notes"], absent=notes["absent"], sources=notes["sources"])
compact = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
flights = {"season": "NW26", "valid": list(SEASON), "updated": board["checked"], "segs": segs}
body = (src.replace("__FLIGHTS_JSON__", compact(flights))
           .replace("__AIRPORTS_JSON__", compact(airports))
           .replace("__MAP_JSON__", compact(geo))
           .replace("__AUDIT_JSON__", compact(audit)))
for mark in ("__FLIGHTS_JSON__", "__AIRPORTS_JSON__", "__MAP_JSON__", "__AUDIT_JSON__"):
    assert mark not in body

# title, fonts and styles come before the app markup; they belong in <head>
split = body.index('<div class="app">')
standalone = (
    '<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="依 TDX 與星宇航空官網時刻表，在世界地圖上推算各航班位置，並提供桃園、清泉崗、高雄的出發／抵達看板、時刻表、航線網路與資料查核。非官方展示。">\n'
    + body[:split] + "</head>\n<body>\n" + body[split:] + "\n</body>\n</html>\n"
)
dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
(dist / "index.html").write_text(standalone, encoding="utf-8")
(dist / "artifact.html").write_text(body, encoding="utf-8")
routes = {tuple(sorted((s["o"], s["d"]))) for s in segs}
print(f"dist/index.html + dist/artifact.html written: {len(body.encode('utf-8')) / 1024:.1f} KB, "
      f"{len(segs)} lines, {len(routes)} routes")
