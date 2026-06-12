import os, json, requests, io, csv, math
from datetime import datetime, timezone, timedelta

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

VN_TZ = timezone(timedelta(hours=7))

# ── ELO CONFIG ──────────────────────────────────────────
K_FACTOR = {"FIFA World Cup": 60, "UEFA Euro": 50, "friendly": 20, "default": 40}
DEFAULT_ELO = 1500
HOME_ADVANTAGE = 100  # World Cup neutral venue → 0


def get_k(tournament: str) -> int:
    for key, val in K_FACTOR.items():
        if key.lower() in tournament.lower():
            return val
    return K_FACTOR["default"]


def expected_score(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def compute_elo_ratings(rows: list) -> dict:
    """Tính ELO từ toàn bộ lịch sử kết quả quốc tế"""
    ratings = {}
    for row in rows:
        home, away = row["home_team"], row["away_team"]
        try:
            hs, as_ = float(row["home_score"]), float(row["away_score"])
        except (ValueError, TypeError):
            continue  # bỏ qua trận chưa có kết quả

        r_h = ratings.get(home, DEFAULT_ELO)
        r_a = ratings.get(away, DEFAULT_ELO)
        neutral = row.get("neutral", "FALSE") == "TRUE"
        adj_h = r_h if neutral else r_h + HOME_ADVANTAGE

        e_h = expected_score(adj_h, r_a)
        e_a = 1 - e_h

        if hs > as_:
            s_h, s_a = 1.0, 0.0
        elif hs < as_:
            s_h, s_a = 0.0, 1.0
        else:
            s_h, s_a = 0.5, 0.5

        # Goal difference multiplier
        gd = abs(hs - as_)
        gd_mult = 1 if gd <= 1 else (1.5 if gd == 2 else (1.75 if gd == 3 else 1.75 + (gd - 3) / 8))

        tourn = row.get("tournament", "")
        k = get_k(tourn)

        ratings[home] = r_h + k * gd_mult * (s_h - e_h)
        ratings[away] = r_a + k * gd_mult * (s_a - e_a)

    return ratings


def predict_from_elo(elo_h: float, elo_a: float, neutral: bool = True) -> dict:
    """Tính xác suất thắng/hòa/thua từ ELO"""
    adj_h = elo_h if neutral else elo_h + HOME_ADVANTAGE
    win_prob = expected_score(adj_h, elo_a)

    # Ước tính xác suất hòa dựa trên độ chênh lệch ELO
    diff = abs(elo_h - elo_a)
    draw_base = 0.28 - (diff / 4000)
    draw_prob = max(0.08, min(0.32, draw_base))

    if win_prob > 0.5:
        home_win = win_prob - draw_prob / 2
        away_win = 1 - home_win - draw_prob
    else:
        away_win = (1 - win_prob) - draw_prob / 2
        home_win = 1 - away_win - draw_prob

    home_win = max(0.05, home_win)
    away_win = max(0.05, away_win)
    draw_prob = max(0.05, draw_prob)

    # Normalize
    total = home_win + draw_prob + away_win
    return {
        "home_win_pct": round(home_win / total * 100, 1),
        "draw_pct": round(draw_prob / total * 100, 1),
        "away_win_pct": round(away_win / total * 100, 1),
    }


def get_recent_form(rows: list, team: str, n: int = 5) -> str:
    """Lấy form 5 trận gần nhất: W/D/L"""
    matches = [r for r in rows
               if team in (r["home_team"], r["away_team"])
               and r["home_score"] not in ("", "NA")
               and r["away_score"] not in ("", "NA")][-n:]
    form = []
    for r in matches:
        try:
            hs, as_ = float(r["home_score"]), float(r["away_score"])
        except Exception:
            continue
        if r["home_team"] == team:
            form.append("W" if hs > as_ else ("D" if hs == as_ else "L"))
        else:
            form.append("W" if as_ > hs else ("D" if hs == as_ else "L"))
    return "".join(form) if form else "N/A"


# ── LẤY DỮ LIỆU ────────────────────────────────────────
def load_match_history() -> list:
    url = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))


def get_dates_to_fetch() -> list:
    """Thứ 6 → lấy 4 ngày (T6+T7+CN+T2), các ngày khác → chỉ hôm nay"""
    now = datetime.now(VN_TZ)
    weekday = now.weekday()  # 0=T2 ... 4=T6
    if weekday == 4:  # Thứ 6
        return [(now + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(4)]
    return [now.strftime("%Y-%m-%d")]


def get_todays_matches() -> list:
    dates = get_dates_to_fetch()
    if len(dates) > 1:
        print(f"📅 Thứ 6 — lấy lịch {len(dates)} ngày: {dates[0]} → {dates[-1]}")
    else:
        print(f"📅 Lấy lịch thi đấu ngày {dates[0]}")

    url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for m in data.get("matches", []):
        if m.get("date") not in dates:
            continue
        time_str = m.get("time", "")
        try:
            tp, tz_p = time_str.split(" ")
            h, mi = map(int, tp.split(":"))
            tz_off = int(tz_p.replace("UTC", ""))
            vn_h = (h - tz_off + 7) % 24
            local_time = f"{vn_h:02d}:{mi:02d}"
        except Exception:
            local_time = "TBD"
        matches.append({
            "home": m["team1"], "away": m["team2"],
            "time": local_time,
            "date": m.get("date"),
            "stage": m.get("group", m.get("round", "World Cup 2026")),
        })

    print(f"✅ {len(matches)} trận")
    return matches


# ── PHÂN TÍCH VỚI GEMINI (ÍT TOKEN) ────────────────────
def analyze_with_gemini(home: str, away: str, elo_h: float, elo_a: float,
                        form_h: str, form_a: str, probs: dict) -> str:
    """Gemini chỉ viết nhận xét ngắn — Python đã tính số rồi"""
    winner = home if probs["home_win_pct"] > probs["away_win_pct"] else (
        away if probs["away_win_pct"] > probs["home_win_pct"] else "Hòa"
    )
    prompt = f"""World Cup 2026: {home} vs {away}
ELO: {home}={round(elo_h)} | {away}={round(elo_a)}
Form 5 trận: {home}={form_h} | {away}={form_a}
Xác suất: {home} thắng {probs['home_win_pct']}% | Hòa {probs['draw_pct']}% | {away} thắng {probs['away_win_pct']}%

Viết 2 câu nhận xét ngắn tiếng Việt về trận này và dự đoán tỉ số. Chỉ trả lời JSON:
{{"comment":"2 câu nhận xét","scoreline":"X-Y","confidence":{round(max(probs['home_win_pct'], probs['away_win_pct']))}}}"""

    import time
    for attempt in range(3):
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 429:
            print(f"  ⏳ Rate limit, chờ {15*(attempt+1)}s...")
            time.sleep(15 * (attempt + 1))
            continue
        resp.raise_for_status()
        break

    data = resp.json()
    if "candidates" not in data:
        raise ValueError(data.get("error", {}).get("message", str(data)))
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        return json.loads(m.group()) if m else {"comment": raw[:100], "scoreline": "?-?", "confidence": 50}


# ── FORMAT & GỬI TELEGRAM ───────────────────────────────
def format_message(results: list, today: str) -> str:
    # Group theo ngày nếu có nhiều ngày (cuối tuần)
    dates = sorted(set(item["match"].get("date", today) for item in results))
    multi_day = len(dates) > 1
    if multi_day:
        date_range = f"{datetime.strptime(dates[0], '%Y-%m-%d').strftime('%d/%m')} - {datetime.strptime(dates[-1], '%Y-%m-%d').strftime('%d/%m/%Y')}"
        header = f"📅 {date_range} (T6→T2) — {len(results)} trận"
    else:
        header = f"📅 {datetime.strptime(today, '%Y-%m-%d').strftime('%d/%m/%Y')} — {len(results)} trận"

    lines = [f"⚽ *DỰ ĐOÁN WORLD CUP 2026*",
             header,
             "━━━━━━━━━━━━━━━━━━"]

    current_date = None

    for i, item in enumerate(results, 1):
        m = item["match"]
        r = item["result"]
        # Hiển thị header ngày mới khi có nhiều ngày
        match_date = m.get("date", today)
        if multi_day and match_date != current_date:
            current_date = match_date
            day_names = {0:"Thứ 2",1:"Thứ 3",2:"Thứ 4",3:"Thứ 5",4:"Thứ 6",5:"Thứ 7",6:"Chủ Nhật"}
            dt = datetime.strptime(match_date, "%Y-%m-%d")
            day_label = day_names[dt.weekday()]
            lines += [f"", f"📆 *{day_label} {dt.strftime('%d/%m')}*"]
        home, away = m["home"], m["away"]
        probs = r["probs"]
        ai = r["ai"]
        elo_h, elo_a = r["elo_home"], r["elo_away"]

        h_pct = probs["home_win_pct"]
        a_pct = probs["away_win_pct"]
        d_pct = probs["draw_pct"]

        if h_pct > a_pct:
            winner_line = f"🏆 *{home}* thắng"
        elif a_pct > h_pct:
            winner_line = f"🏆 *{away}* thắng"
        else:
            winner_line = "🤝 *Hòa*"

        conf = ai.get("confidence", round(max(h_pct, a_pct)))
        filled = round(conf / 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)
        score = ai.get("scoreline", "?-?")
        comment = ai.get("comment", "")

        lines += [
            f"\n*{i}. {home} 🆚 {away}*",
            f"🕐 {m['time']} VN  |  {m['stage']}",
            f"",
            f"{winner_line}  ({score})",
            f"{bar} {conf}%",
            f"",
            f"📊 {home}: {h_pct}%  |  Hòa: {d_pct}%  |  {away}: {a_pct}%",
            f"🔢 ELO: {home} *{round(elo_h)}* vs {away} *{round(elo_a)}*",
            f"📈 Form: {home} `{r['form_home']}`  |  {away} `{r['form_away']}`",
        ]
        if comment:
            lines += [f"", f"💬 _{comment}_"]
        lines.append("━━━━━━━━━━━━━━━━━━")

    lines += ["", "🤖 _ELO + Gemini AI_",
              "_⚠️ Dự đoán tham khảo, bóng đá luôn có bất ngờ!_"]
    return "\n".join(lines)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID, "text": message,
        "parse_mode": "Markdown", "disable_web_page_preview": True,
    }, timeout=15)
    resp.raise_for_status()
    print(f"✅ Telegram: {resp.json().get('ok')}")


# ── MAIN ────────────────────────────────────────────────
def main():
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"🚀 Bắt đầu {datetime.now(VN_TZ).strftime('%H:%M')} ngày {today}")

    # Load 1 lần dùng cho cả ELO lẫn form
    print("📥 Đang tải lịch sử kết quả (~50k trận)...")
    history = load_match_history()
    print(f"✅ {len(history)} trận lịch sử")

    print("⚙️ Tính ELO ratings...")
    elo_ratings = compute_elo_ratings(history)
    print(f"✅ {len(elo_ratings)} đội có ELO")

    matches = get_todays_matches()
    if not matches:
        send_telegram(f"⚽ *WORLD CUP 2026*\n📅 {datetime.now(VN_TZ).strftime('%d/%m/%Y')}\n\n😴 Hôm nay không có trận đấu.")
        return

    results = []
    for match in matches:
        home, away = match["home"], match["away"]
        print(f"🔍 {home} vs {away}...")

        elo_h = elo_ratings.get(home, DEFAULT_ELO)
        elo_a = elo_ratings.get(away, DEFAULT_ELO)
        form_h = get_recent_form(history, home)
        form_a = get_recent_form(history, away)
        probs = predict_from_elo(elo_h, elo_a, neutral=True)

        print(f"  ELO: {home}={round(elo_h)} | {away}={round(elo_a)}")
        print(f"  Xác suất: {probs}")

        try:
            ai = analyze_with_gemini(home, away, elo_h, elo_a, form_h, form_a, probs)
            print(f"  AI: {ai.get('scoreline')} | {ai.get('confidence')}%")
        except Exception as e:
            print(f"  ❌ Gemini lỗi: {e}")
            ai = {"comment": "Không thể lấy nhận xét AI.", "scoreline": "?-?",
                  "confidence": round(max(probs["home_win_pct"], probs["away_win_pct"]))}

        results.append({"match": match, "result": {
            "probs": probs, "ai": ai,
            "elo_home": elo_h, "elo_away": elo_a,
            "form_home": form_h, "form_away": form_a,
        }})

    send_telegram(format_message(results, today))
    print("🎉 Hoàn thành!")


if __name__ == "__main__":
    main()
