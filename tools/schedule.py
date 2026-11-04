"""Parse the timetable files into a list of flight segments (shared by the other tools)."""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "data" / "schedule-nw26.txt"
SAMPLES = ROOT / "data" / "official-samples.txt"
SEASON = ("2026-11-02", "2027-03-27")
LINE = re.compile(r"^(JX\d+)\s+([A-Z]{3})\s+(\d\d:\d\d)\s+([A-Z]{3})\s+(\d\d:\d\d)([+-]\d)?\s+(D|[1-7]+)\s+(\S+)((?:\s+\w+=\S+)*)\s*$")
OPTIONS = ("from", "to", "skip", "only", "op", "ex")
# Taoyuan lists JX7300/7301 beside Etihad's EY898/899, at the same times, with no aircraft of Starlux's own.
PARTNER = {"JX7300": "EY898", "JX7301": "EY899"}


def kind(no):
    """JX flown by Starlux, CS flown by a partner under a JX number."""
    return "CS" if no in PARTNER else "JX"


def parse(path=SCHEDULE):
    segs = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line: continue
        m = LINE.match(line)
        if not m: raise ValueError(f"{path.name}:{n}: cannot parse {raw!r}")
        no, o, dep, d, arr, plus, days, ac, opts = m.groups()
        seg = {"no": no, "o": o, "d": d, "dep": dep, "arr": arr, "plus": int(plus or 0), "ac": ac, "kind": kind(no),
               "days": "1234567" if days == "D" else "".join(sorted(set(days)))}
        for kv in opts.split():
            k, v = kv.split("=", 1)
            if k not in OPTIONS: raise ValueError(f"{path.name}:{n}: unknown option {k}")
            seg[k] = v
        segs.append(seg)
    return segs


def operates(s, day):
    """Does segment s leave on this date (a datetime.date, origin local)?"""
    k = day.isoformat()
    if not SEASON[0] <= k <= SEASON[1]: return False
    if "only" in s: return k in s["only"].split(",")
    return str(day.isoweekday()) in s["days"] and not ("from" in s and k < s["from"]) and not ("to" in s and k > s["to"]) \
        and k not in s.get("skip", "").split(",")


def read_samples(path=SAMPLES):
    """Official timetable pages as read: [(centre date, origin, destination, flight rows)]; a page with no flights has no rows."""
    pages = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        f = raw.split("#", 1)[0].split()
        if not f: continue
        rows = pages.setdefault((f[0], f[1], f[2]), [])
        if f[3] != "none":
            no, ac, dep, arr, flags = f[3:]
            rows.append(dict(no="JX" + no, ac=ac, dep=dep, arr=arr, flags=flags))
    return [(c, o, d, rows) for (c, o, d), rows in pages.items()]
