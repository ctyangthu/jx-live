# 星宇航空航班動態系統

依 TDX 國際定期航班與星宇航空官網時刻表（2026/11/2–2027/3/27），在世界地圖上推算每一個航班的位置，並提供桃園、松山、清泉崗、高雄的出發／抵達看板、時刻表、航線網路與資料查核。

網址：https://ctyangthu.github.io/jx-live/

## 查核結果（2026/11/4）

| 機場 | 官網自營航線 | 本系統 | 說明 |
|---|---:|---:|---|
| 桃園 TPE | 33 | 33 | 另有阿提哈德共掛（阿布達比）與關島包機 |
| 清泉崗 RMQ | 12 | 10 | 峴港、富國島官網仍列，抽查週都查無航班 |
| 高雄 KHH | 2 | 2 | 神戶、沖繩，2027/1/1 開航 |
| 松山 TSA | 0 | 0 | 星宇沒有松山國際線 |

只看 TDX 會漏掉這些，已補入（`data/extra-flights.txt`）：

| 航班 | 航段 | 日期 | 來源 |
|---|---|---|---|
| JX360／361、JX362／363 | 高雄—神戶、高雄—沖繩 | 2027/1/1 起每日 | 官網、AeroRoutes |
| JX824／825 | 桃園—大阪第三班 | 1/15 起每日 | 官網、AeroRoutes |
| JX201／3201／202 | 桃園—澳門 | 週五 12/4 起；週二、六、日 2/2 起 | 官網 |
| JX842／843 | 桃園—福岡 | 週日 12/6 起 | 官網 |
| JX838／839 | 桃園—名古屋 | 週四 12/3–12/31 | 官網 |
| JX1233／1234 | 桃園—香港加班 | 12/17、12/31 | 官網 |
| JX715／716 | 桃園—河內 | 週二 1/5 起 | 官網 |
| JX900／901、JX902／903 | 桃園—釜山 | 週一 3/1 起、週五 3/5 起 | 官網 |
| 清泉崗全部 26 個班號 | | 1/4–3/27（TDX 只到 1/3） | 官網 |
| JX8072／8071 | 桃園—關島包機 | 2/4、2/8、2/12 | 只有 AeroRoutes |

JX7300／7301（阿布達比）是阿提哈德 EY898／899 的共掛班號，預設隱藏。

比對結果：官網抽查 245 頁、1,875 個航班日，未收錄 0；桃園看板 11/3–11/5 的 223 筆未收錄 0、時刻差 0；清泉崗一週班號表 26 個全部相符。

## 限制

- **官網只抽查，不是逐週全掃。** 桃園去程的全部航線查過 11/9–15、12/14–20、1/18–24、2/8–14、3/8–14 這五週；清泉崗去程查過 12/14–20、1/4–10、2/8–14、3/8–14；高雄查過 1/4 前後與 2/8–14、3/8–14；回程只查了部分航線。其餘週次沒有全部查過。TDX 的掉班是抽查才發現的，未抽查的週次仍可能有遺漏，特別是 12/21–1/3 年底假期和 2 月農曆年後。
- 補入航班的中間週次依前後規律推定；JX842 週日時刻的切換日、JX1234 12/31 的時刻都是推定。
- 官網資料以一般瀏覽方式讀取公開頁面，沒有呼叫官網內部 API，所以 `data/official-samples.txt` 是手動記錄、無法自動更新。
- 班表起點是 2026/11/2：TDX 從這天開始，11/2–11/3 被移除的 21 班依下一週回填，10/25–11/1 沒有資料。
- 航班狀態與位置依表定時間推算，不含延誤、取消、改降等即時資訊。機型依抽查週常見程度排列，個別日期可能不同。
- 本系統為非官方展示，與星宇航空無關，實際航班請以星宇航空公告為準。

## 建置

```bash
python3 tools/build.py
```

更新班表時，依序執行（TDX 未帶金鑰每天只能查幾次，可設定 `TDX_TOKEN`）：

```bash
python3 tools/fetch_tdx.py
```

```bash
python3 tools/build_schedule.py
```

```bash
python3 tools/check_schedule.py
```

```bash
python3 tools/audit_official.py
```

```bash
python3 tools/audit_airports.py
```

```bash
python3 tools/build.py
```

## 資料來源

[星宇航空班機時刻表](https://www.starlux-airlines.com/zh-TW/timetable)、[TDX](https://tdx.transportdata.tw/)、[桃園機場](https://www.taoyuan-airport.com/)、[松山機場](https://www.tsa.gov.tw/flights/international/regular)、[清泉崗機場](https://www.tca.gov.tw/?act=fids&code=regular_flight)、[高雄機場](https://www.kia.gov.tw/FLIPLAN.html)、[AeroRoutes](https://www.aeroroutes.com/eng/tag/Starlux+Airlines)、[維基百科](https://zh.wikipedia.org/zh-tw/星宇航空航點)（只用來找可能遺漏的航點）。地圖：[world-atlas](https://github.com/topojson/world-atlas)（Natural Earth 1:50m）。
