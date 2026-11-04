"""Compare the timetable with the official pages recorded in data/official-samples.txt and with the official route list.

    python3 tools/audit_official.py

Writes data/audit-official.json for the 查核 tab. The official pages show one representative time per flight, while TDX
moves departures by a few minutes day by day and matches Taoyuan's board, so a time difference does not change the
timetable; it is only listed. A flight that is on a page but not in the timetable, or the reverse, would be a real gap.
"""
import collections, datetime as dt, json
from schedule import ROOT, SEASON, kind, operates, parse, read_samples


def tdx_days():
    doc = json.loads((ROOT / "data" / "tdx-snapshot.json").read_text(encoding="utf-8"))
    seen = set()
    for no, o, d, _, _, start, end, days in doc["rows"]:
        a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        for n in range((b - a).days + 1):
            day = a + dt.timedelta(days=n)
            if str(day.isoweekday()) in days: seen.add((day, no, o, d))
    return seen


def main():
    segs, pages, tdx = parse(), read_samples(), tdx_days()
    missing, extra, moved, not_in_tdx = [], [], collections.defaultdict(list), collections.defaultdict(list)
    compared = same = 0
    for c, o, d, rows in pages:
        centre = dt.date.fromisoformat(c)
        for i in range(7):
            day = centre + dt.timedelta(days=i - 3)
            if not SEASON[0] <= day.isoformat() <= SEASON[1]: continue
            page = {r["no"]: r for r in rows if r["flags"][i] == "1"}
            ours = {s["no"]: s for s in segs if s["o"] == o and s["d"] == d and operates(s, day) and kind(s["no"]) == "JX" and s.get("ex") != "chr"}
            for no in sorted(set(page) | set(ours)):
                compared += 1
                tag = dict(day=day.isoformat(), no=no, o=o, d=d)
                if no not in ours: missing.append(tag); continue
                if no not in page: extra.append(tag); continue
                if (page[no]["dep"], page[no]["arr"]) == (ours[no]["dep"], ours[no]["arr"]): same += 1
                else: moved[no, o, d, f'{page[no]["dep"]}-{page[no]["arr"]}', f'{ours[no]["dep"]}-{ours[no]["arr"]}'].append(day.isoformat())
                if (day, no, o, d) not in tdx: not_in_tdx[no, o, d].append(day.isoformat())

    routes = json.loads((ROOT / "data" / "official-routes.json").read_text(encoding="utf-8"))
    ours_routes = collections.defaultdict(set)
    for s in segs:
        if s["o"] in routes["routes"]: ours_routes[s["o"]].add((s["d"], s["kind"], s.get("ex")))
    table = []
    for ap, listed in routes["routes"].items():
        flown = {d for d, k, ex in ours_routes[ap] if k == "JX" and ex != "chr"}
        table.append(dict(airport=ap, official=len(listed), ours=len(flown), official_only=sorted(set(listed) - flown), ours_only=sorted(flown - set(listed)),
                          partner=sorted({d for d, k, _ in ours_routes[ap] if k == "CS"}), charter=sorted({d for d, _, ex in ours_routes[ap] if ex == "chr"})))

    weeks = sorted({c for c, *_ in pages})
    out = dict(checked=routes["checked"], pages=len(pages), weeks=weeks, compared=compared, same=same, missing=missing, extra=extra,
               empty=[dict(day=c, o=o, d=d) for c, o, d, rows in pages if not rows],
               time_diffs=[dict(no=k[0], o=k[1], d=k[2], official=k[3], ours=k[4], n=len(v), first=min(v), last=max(v))
                           for k, v in sorted(moved.items(), key=lambda kv: (int(kv[0][0][2:]), kv[0][3]))],
               not_in_tdx=[dict(no=k[0], o=k[1], d=k[2], n=len(v), first=min(v), last=max(v)) for k, v in sorted(not_in_tdx.items(), key=lambda kv: int(kv[0][0][2:]))],
               routes=table, partner_only=routes["partner_only"], listed_without_route=routes["listed_without_route"])
    (ROOT / "data" / "audit-official.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(pages)} official pages, {compared} flight days compared, {same} with identical times")
    print(f"on an official page but not in the timetable: {len(missing)}")
    for r in missing[:40]: print("  ", *r.values())
    print(f"in the timetable but not on the official page: {len(extra)}")
    for r in extra[:40]: print("  ", *r.values())
    print(f"time differences: {sum(r['n'] for r in out['time_diffs'])} flight days in {len(out['time_diffs'])} groups")
    print("official flights not in TDX:", [f"{r['no']} {r['o']}-{r['d']} ×{r['n']}" for r in out["not_in_tdx"]])
    for r in table: print(r)


if __name__ == "__main__":
    main()
