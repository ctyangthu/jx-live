"""Build data/schedule-nw26.txt from TDX and the official timetable, and write data/audit-sources.json.

    python3 tools/build_schedule.py

TDX is the backbone: its times match Taoyuan's board exactly and change day by day. Around it:
  - TDX drops the days of the current week that have passed, so 11/2 and 11/3 are filled from the same weekday a week on;
  - TDX loads Taichung only to 2027/1/3. The official timetable shows the same pattern on the weeks sampled (1/4–1/10,
    2/8–2/14, 3/8–3/14), so its 1/4–1/10 page is used from 1/4 to the end of the season;
  - flights TDX has not listed yet come from data/extra-flights.txt.
TDX has no aircraft: those come from the official pages sampled, a return flight taking its outbound's aircraft.
"""
import collections, datetime as dt, json, re
from schedule import ROOT, SCHEDULE, SEASON, PARTNER, parse, read_samples

S0, S1 = dt.date.fromisoformat(SEASON[0]), dt.date.fromisoformat(SEASON[1])
ONE = dt.timedelta(days=1)
AC_CODE = {"A321neo": "32Q", "A330-900neo": "339", "A350-900": "359", "A350-1000": "351"}
AC_PARTNER = {"JX7300": "789", "JX7301": "789"}   # Taoyuan's board shows B787-9 on EY898/899
RMQ_PAGE = "2027-01-07"
RMQ_FROM = dt.date(2027, 1, 4)


def split_time(arr):
    m = re.fullmatch(r"(\d\d:\d\d)([+-]\d)?", arr)
    return m.group(1), int(m.group(2) or 0)


def plus_text(n):
    return f"{n:+d}" if n else ""


def load_tdx():
    doc = json.loads((ROOT / "data" / "tdx-snapshot.json").read_text(encoding="utf-8"))
    out = {}
    for no, o, d, dep, arr, start, end, days in doc["rows"]:
        a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        for n in range((b - a).days + 1):
            day = a + n * ONE
            if S0 <= day <= S1 and str(day.isoweekday()) in days:
                out[day, no, o, d] = (dep, arr)
    return doc, out


def fold(dates):
    """Dates → [(weekdays, from, to, skip, only)], one entry per line, with the shortest description.
    A long gap starts a new line."""
    dates = sorted(dates)
    if len(dates) <= 6:
        wds = {d.isoweekday() for d in dates}
        a, b = dates[0], dates[-1]
        full = [a + n * ONE for n in range((b - a).days + 1) if (a + n * ONE).isoweekday() in wds]
        if len(full) != len(dates): return [(wds, None, None, [], dates)]
    runs, cur = [], [dates[0]]
    for d in dates[1:]:
        if (d - cur[-1]).days > 21: runs.append(cur); cur = []
        cur.append(d)
    runs.append(cur)
    out = []
    for run in runs:
        wds = {d.isoweekday() for d in run}
        a, b = run[0], run[-1]
        full = [a + n * ONE for n in range((b - a).days + 1) if (a + n * ONE).isoweekday() in wds]
        skip = sorted(set(full) - set(run))
        if len(skip) >= len(run): out.append((wds, None, None, [], run)); continue
        # a bound is only needed if the flight would otherwise run on more days of the season
        before = any((S0 + n * ONE).isoweekday() in wds for n in range((a - S0).days))
        after = any((b + (n + 1) * ONE).isoweekday() in wds for n in range((S1 - b).days))
        out.append((wds, a if before else None, b if after else None, skip, []))
    return out


def aircraft(pages):
    """(no, o, d) → aircraft list, most common first, from the official pages sampled."""
    seen = collections.defaultdict(collections.Counter)
    for c, o, d, rows in pages:
        for r in rows:
            seen[r["no"], o, d][AC_CODE[r["ac"]]] += r["flags"].count("1")

    def base(no):      # JX1834 → JX834, JX3201 → JX201: extra flights of a regular one
        n = int(no[2:])
        return f"JX{n % 1000}" if n >= 1000 else no

    def lookup(no, o, d):
        if no in AC_PARTNER: return AC_PARTNER[no]
        n = int(no[2:])
        tries = [(no, o, d), (f"JX{n - 1}", d, o), (f"JX{n + 1}", d, o), (base(no), o, d),
                 (f"JX{int(base(no)[2:]) - 1}", d, o), (f"JX{int(base(no)[2:]) + 1}", d, o)]
        for k in tries:
            if k in seen: return "/".join(a for a, _ in seen[k].most_common())
        routes = collections.Counter()
        for (_, a, b), c in seen.items():
            if {a, b} == {o, d}: routes.update(c)
        return "/".join(a for a, _ in routes.most_common()) or "EQV"
    return lookup


def rmq_lines(pages):
    """Taichung after TDX stops: the official page centred on 1/7 is a Monday-to-Sunday week."""
    out = []
    for c, o, d, rows in pages:
        if c != RMQ_PAGE or "RMQ" not in (o, d): continue
        for r in rows:
            days = "".join(str(i + 1) for i, f in enumerate(r["flags"]) if f == "1")
            out.append((int(r["no"][2:]), r["no"], o, d, r["dep"], r["arr"], "D" if len(days) == 7 else days, AC_CODE[r["ac"]]))
    return [f"{no:7}{o} {dep}  {d} {arr:9}{days:8}{ac:12}from={RMQ_FROM} ex=off" for _, no, o, d, dep, arr, days, ac in sorted(out)]


def main():
    tdx_doc, tdx = load_tdx()
    pages = read_samples()
    ac_of = aircraft(pages)

    # the days TDX has dropped
    filled = collections.defaultdict(list)
    for day in (dt.date(2026, 11, 2), dt.date(2026, 11, 3)):
        for (d7, no, o, d), times in list(tdx.items()):
            if d7 == day + 7 * ONE and (day, no, o, d) not in tdx:
                tdx[day, no, o, d] = times
                filled[no, o, d].append(day.isoformat())

    groups = collections.defaultdict(list)
    for (day, no, o, d), (dep, arr) in tdx.items():
        groups[no, o, d, dep, arr].append(day)

    lines = []
    for (no, o, d, dep, arr), dates in groups.items():
        hhmm, plus = split_time(arr)
        ac = ac_of(no, o, d)
        for wds, a, b, skip, only in fold(dates):
            days = "D" if len(wds) == 7 else "".join(str(x) for x in sorted(wds))
            opts = []
            if a: opts.append(f"from={a}")
            if b: opts.append(f"to={b}")
            if skip: opts.append("skip=" + ",".join(map(str, skip)))
            if only: opts.append("only=" + ",".join(map(str, only)))
            if no in PARTNER: opts.append(f"op={PARTNER[no]}")
            first = min(only) if only else (a or min(dates))
            lines.append(((int(no[2:]), no, o, dep, first),
                          f"{no:7}{o} {dep}  {d} {hhmm}{plus_text(plus):3} {days:8}{ac:12}{' '.join(opts)}".rstrip()))
    lines.sort()

    head = f"""# 星宇航空國際線班表 · 2026/11/2–2027/3/27
# 由 tools/build_schedule.py 產生，請勿手動修改；手動補充的航班寫在 data/extra-flights.txt。
#
# 每行一個航段：航班  出發機場 表定起飛  抵達機場 表定抵達[±天數]  星期  機型  [選項]
#   時間皆為當地時間；+1、+2 表示抵達日為起飛日（出發地日期）後一、二天；-1 表示越過換日線、當地日期早一天（JX12）
#   星期：D＝每日；數字為行駛星期（1＝週一 … 7＝週日），以出發地日期計
#   選項：from=/to= 只在該期間行駛；skip= 該日停飛；only= 只在這些日期行駛
#         op= 實際執飛的航班（JX7300、JX7301 為阿提哈德執飛的共掛班號）
#         ex=off 官網時刻表有、TDX 尚未收錄；ex=chr 官網時刻表查不到的包機
#   機型依官網抽樣週（2026/11/9–15、2027/1/18–24）常見程度排列，個別日期可能不同。
#
# 來源：TDX 國際定期航班（{tdx_doc['fetched']} 抓取）、星宇官網班機時刻表（data/official-samples.txt）。
"""
    extra = (ROOT / "data" / "extra-flights.txt").read_text(encoding="utf-8")
    extra_lines = [l for l in extra.splitlines() if l.strip() and not l.startswith("#")]
    SCHEDULE.write_text(head + "\n" + "\n".join(l for _, l in lines) +
                        f"\n\n# 清泉崗：TDX 只到 2027/1/3，{RMQ_FROM} 起依官網時刻表\n" + "\n".join(rmq_lines(pages)) +
                        "\n\n# TDX 尚未收錄（data/extra-flights.txt）\n" + "\n".join(extra_lines) + "\n", encoding="utf-8")

    last = {}
    for day, no, o, d in tdx:
        for ap in (o, d):
            if ap in ("TPE", "TSA", "KHH", "RMQ"): last[ap] = max(last.get(ap, day), day)
    out = dict(tdx=dict(fetched=tdx_doc["fetched"], rows=len(tdx_doc["rows"]), flight_days=len(tdx), last={k: v.isoformat() for k, v in sorted(last.items())}),
               filled=[dict(no=k[0], o=k[1], d=k[2], dates=v) for k, v in sorted(filled.items(), key=lambda kv: (int(kv[0][0][2:]), kv[0][1]))])
    (ROOT / "data" / "audit-sources.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    segs = parse()
    print(f"{len(segs)} lines; {len(tdx)} TDX flight days, {sum(len(v) for v in filled.values())} of them filled in; kinds:", dict(collections.Counter(s['kind'] for s in segs)))
    no_ac = sorted({s["no"] for s in segs if s["ac"] == "EQV"})
    if no_ac: print("no aircraft for:", no_ac)


if __name__ == "__main__":
    main()
