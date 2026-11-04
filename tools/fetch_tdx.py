"""Download the week-by-week international schedule from TDX into data/tdx-snapshot.json.

    TDX_TOKEN=... python3 tools/fetch_tdx.py        # token from a TDX account
    python3 tools/fetch_tdx.py jx.json              # or from a response already saved

Without a token TDX answers a few queries a day, then "401 Valid API Key Required".
"""
import datetime as dt, json, os, pathlib, re, sys, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://tdx.transportdata.tw/api/basic/v2/Air/GeneralSchedule/International?"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get():
    url = BASE + urllib.parse.urlencode({"$filter": "AirlineID eq 'JX'", "$format": "JSON"})
    headers = {"User-Agent": "jx-live timetable audit"}
    if os.environ.get("TDX_TOKEN"): headers["Authorization"] = "Bearer " + os.environ["TDX_TOKEN"]
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120).read())


def main(files):
    response = json.loads(pathlib.Path(files[0]).read_text(encoding="utf-8")) if files else get()
    rows, seen = [], set()
    for r in response:
        no = re.sub(r"^JX0*", "JX", r["FlightNumber"])
        days = "".join(str(i + 1) for i, d in enumerate(DAYS) if r[d])
        row = [no, r["DepartureAirportID"], r["ArrivalAirportID"], r["DepartureTime"], r["ArrivalTime"], r["ScheduleStartDate"], r["ScheduleEndDate"], days]
        if tuple(row) not in seen:
            seen.add(tuple(row)); rows.append(row)
    rows.sort(key=lambda r: (int(r[0][2:]), r[5], r[3]))
    out = dict(fetched=dt.date.today().isoformat(), fields=["no", "o", "d", "dep", "arr", "start", "end", "days"], rows=rows)
    (ROOT / "data" / "tdx-snapshot.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("],[", "],\n["), encoding="utf-8")
    print(f"{len(rows)} TDX rows, {out['fetched']}")


if __name__ == "__main__":
    main(sys.argv[1:])
