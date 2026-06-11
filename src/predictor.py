import os
import json
import requests
from datetime import datetime, timezone, timedelta

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

VN_TZ = timezone(timedelta(hours=7))


def get_todays_matches():
    """Lấy lịch WC2026 từ openfootball/worldcup.json — free, no API key"""
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"📅 Tìm trận đấu ngày: {today}")

    try:
        url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        matches = []
        for m in data.get("matches", []):
            match_date = m.get("date", "")
            if match_date != today:
                continue
            # Parse giờ: "13:00 UTC-6" → giờ VN (UTC+7 = UTC-6 + 13h)
            time_str = m.get("time", "")
            try:
                time_part, tz_part = time_str.split(" ")
                h, mi = map(int, time_part.split(":"))
                tz_offset = int(tz_part.replace("UTC", ""))
                # Chuyển sang UTC rồi sang VN
                utc_h = h - tz_offset
                vn_h = (utc_h + 7) % 24
                local_time = f"{vn_h:02d}:{mi:02d}"
            except Exception:
                local_time = "TBD"

            stage = m.get("group", m.get("round", "World Cup 2026"))
            matches.append({
                "home": m["team1"],
                "away": m["team2"],
                "time": local_time,
                "stage": stage,
            })
        if matches:
            print(f"✅ openfootball: {len(matches)} trận hôm nay")
            return matches
        print("⚠️ openfootball: không có trận hôm nay")
    except Exception as e:
        print(f"⚠️ openfootball lỗi: {e}")

    print("⚠️ Fallback hardcode")
    return get_hardcoded_schedule(today)


def get_hardcoded_schedule(today: str):
    # Tất cả giờ là giờ VN (UTC+7). ET+11 = VN
    # Nguồn: ESPN / CBS Sports lịch chính thức WC2026
    schedule = {
        # ── VÒNG BẢNG ──
        "2026-06-11": [
            {"home": "Mexico",      "away": "South Africa", "time": "02:00", "stage": "Bảng A"},
            {"home": "South Korea", "away": "Czechia",      "time": "09:00", "stage": "Bảng A"},
        ],
        "2026-06-12": [
            {"home": "Canada",  "away": "Bosnia Herzegovina","time": "02:00", "stage": "Bảng B"},
            {"home": "USA",     "away": "Paraguay",          "time": "08:00", "stage": "Bảng D"},
        ],
        "2026-06-13": [
            {"home": "Qatar",      "away": "Switzerland",  "time": "02:00", "stage": "Bảng B"},
            {"home": "Brazil",     "away": "Morocco",      "time": "05:00", "stage": "Bảng C"},
            {"home": "Haiti",      "away": "Scotland",     "time": "08:00", "stage": "Bảng C"},
            {"home": "Australia",  "away": "Turkiye",      "time": "11:00", "stage": "Bảng D"},
        ],
        "2026-06-14": [
            {"home": "Germany",    "away": "Curacao",      "time": "00:00", "stage": "Bảng E"},
            {"home": "Netherlands","away": "Japan",        "time": "03:00", "stage": "Bảng F"},
            {"home": "Ivory Coast","away": "Ecuador",      "time": "06:00", "stage": "Bảng E"},
            {"home": "Sweden",     "away": "Tunisia",      "time": "09:00", "stage": "Bảng F"},
        ],
        "2026-06-15": [
            {"home": "Spain",        "away": "Cape Verde",  "time": "23:00", "stage": "Bảng H"},
            {"home": "Belgium",      "away": "Egypt",       "time": "02:00", "stage": "Bảng G"},
            {"home": "Saudi Arabia", "away": "Uruguay",     "time": "05:00", "stage": "Bảng H"},
            {"home": "Iran",         "away": "New Zealand", "time": "08:00", "stage": "Bảng G"},
        ],
        "2026-06-16": [
            {"home": "France",    "away": "Senegal",   "time": "02:00", "stage": "Bảng I"},
            {"home": "Iraq",      "away": "Norway",    "time": "05:00", "stage": "Bảng I"},
            {"home": "Argentina", "away": "Algeria",   "time": "08:00", "stage": "Bảng J"},
            {"home": "Austria",   "away": "Jordan",    "time": "11:00", "stage": "Bảng J"},
        ],
        "2026-06-17": [
            {"home": "Portugal",  "away": "DR Congo",  "time": "02:00", "stage": "Bảng K"},
            {"home": "England",   "away": "Croatia",   "time": "05:00", "stage": "Bảng L"},
            {"home": "Ghana",     "away": "Panama",    "time": "08:00", "stage": "Bảng L"},
        ],
        "2026-06-18": [
            {"home": "Uzbekistan","away": "Colombia",     "time": "01:00", "stage": "Bảng K"},
            {"home": "Czechia",   "away": "South Africa", "time": "23:00", "stage": "Bảng A"},
            {"home": "Mexico",    "away": "South Korea",  "time": "23:00", "stage": "Bảng A"},
        ],
        "2026-06-19": [
            {"home": "Switzerland","away": "Bosnia Herzegovina","time": "02:00", "stage": "Bảng B"},
            {"home": "Canada",     "away": "Qatar",            "time": "05:00", "stage": "Bảng B"},
            {"home": "Paraguay",   "away": "Australia",        "time": "23:00", "stage": "Bảng D"},
            {"home": "USA",        "away": "Turkiye",          "time": "23:00", "stage": "Bảng D"},
        ],
        "2026-06-20": [
            {"home": "Morocco",    "away": "Haiti",     "time": "02:00", "stage": "Bảng C"},
            {"home": "Scotland",   "away": "Brazil",    "time": "05:00", "stage": "Bảng C"},
            {"home": "Japan",      "away": "Sweden",    "time": "23:00", "stage": "Bảng F"},
            {"home": "Tunisia",    "away": "Netherlands","time": "23:00", "stage": "Bảng F"},
        ],
        "2026-06-21": [
            {"home": "Spain",    "away": "Saudi Arabia", "time": "23:00", "stage": "Bảng H"},
            {"home": "Belgium",  "away": "Iran",         "time": "02:00", "stage": "Bảng G"},
            {"home": "Uruguay",  "away": "Cape Verde",   "time": "05:00", "stage": "Bảng H"},
            {"home": "Egypt",    "away": "New Zealand",  "time": "08:00", "stage": "Bảng G"},
        ],
        "2026-06-22": [
            {"home": "Argentina","away": "Austria",  "time": "00:00", "stage": "Bảng J"},
            {"home": "France",   "away": "Iraq",     "time": "04:00", "stage": "Bảng I"},
            {"home": "Norway",   "away": "Senegal",  "time": "07:00", "stage": "Bảng I"},
            {"home": "Jordan",   "away": "Algeria",  "time": "10:00", "stage": "Bảng J"},
        ],
        "2026-06-23": [
            {"home": "Portugal",  "away": "Uzbekistan","time": "00:00", "stage": "Bảng K"},
            {"home": "England",   "away": "Ghana",     "time": "03:00", "stage": "Bảng L"},
            {"home": "Panama",    "away": "Croatia",   "time": "06:00", "stage": "Bảng L"},
            {"home": "Colombia",  "away": "DR Congo",  "time": "09:00", "stage": "Bảng K"},
        ],
        "2026-06-24": [
            {"home": "Switzerland","away": "Canada",              "time": "02:00", "stage": "Bảng B"},
            {"home": "Bosnia Herzegovina","away": "Qatar",        "time": "02:00", "stage": "Bảng B"},
            {"home": "Scotland",   "away": "Brazil",              "time": "05:00", "stage": "Bảng C"},
            {"home": "Morocco",    "away": "Haiti",               "time": "05:00", "stage": "Bảng C"},
            {"home": "Czechia",    "away": "Mexico",              "time": "08:00", "stage": "Bảng A"},
            {"home": "South Africa","away": "South Korea",        "time": "08:00", "stage": "Bảng A"},
        ],
        "2026-06-25": [
            {"home": "Ecuador",    "away": "Germany",      "time": "03:00", "stage": "Bảng E"},
            {"home": "Curacao",    "away": "Ivory Coast",  "time": "03:00", "stage": "Bảng E"},
            {"home": "Japan",      "away": "Sweden",       "time": "06:00", "stage": "Bảng F"},
            {"home": "Tunisia",    "away": "Netherlands",  "time": "06:00", "stage": "Bảng F"},
            {"home": "Turkiye",    "away": "USA",          "time": "09:00", "stage": "Bảng D"},
            {"home": "Paraguay",   "away": "Australia",    "time": "09:00", "stage": "Bảng D"},
        ],
        "2026-06-26": [
            {"home": "Norway",     "away": "France",       "time": "02:00", "stage": "Bảng I"},
            {"home": "Senegal",    "away": "Iraq",         "time": "02:00", "stage": "Bảng I"},
            {"home": "Algeria",    "away": "Argentina",    "time": "05:00", "stage": "Bảng J"},
            {"home": "Jordan",     "away": "Austria",      "time": "05:00", "stage": "Bảng J"},
            {"home": "Cape Verde", "away": "Saudi Arabia", "time": "07:00", "stage": "Bảng H"},
            {"home": "Uruguay",    "away": "Spain",        "time": "07:00", "stage": "Bảng H"},
        ],
        "2026-06-27": [
            {"home": "New Zealand","away": "Belgium",      "time": "02:00", "stage": "Bảng G"},
            {"home": "Iran",       "away": "Egypt",        "time": "02:00", "stage": "Bảng G"},
            {"home": "DR Congo",   "away": "Portugal",     "time": "05:00", "stage": "Bảng K"},
            {"home": "Colombia",   "away": "Uzbekistan",   "time": "05:00", "stage": "Bảng K"},
            {"home": "Croatia",    "away": "England",      "time": "08:00", "stage": "Bảng L"},
            {"home": "Panama",     "away": "Ghana",        "time": "08:00", "stage": "Bảng L"},
        ],
    }
    return schedule.get(today, [])


def analyze_match_with_ai(home: str, away: str, stage: str) -> dict:
    prompt = f"""Bạn là chuyên gia phân tích bóng đá World Cup 2026.

Trận đấu: {home} vs {away}
Giai đoạn: {stage}

Hãy phân tích và dự đoán kết quả. Trả lời CHỈ bằng JSON hợp lệ (không markdown, không backtick):
{{
  "winner": "tên đội thắng hoặc Hòa",
  "confidence": số từ 50 đến 82,
  "scoreline": "ví dụ 2-1",
  "home_win_pct": số,
  "draw_pct": số,
  "away_win_pct": số,
  "key_factors": ["yếu tố 1", "yếu tố 2", "yếu tố 3"],
  "analysis": "2-3 câu phân tích ngắn gọn bằng tiếng Việt"
}}"""

    import time
    for attempt in range(3):
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if response.status_code == 429:
            print(f"  ⏳ Rate limit, chờ {15*(attempt+1)}s...")
            time.sleep(15 * (attempt + 1))
            continue
        response.raise_for_status()
        break
    data = response.json()
    # Debug nếu không có candidates
    if "candidates" not in data:
        error_msg = data.get("error", {}).get("message", str(data))
        raise ValueError(f"Gemini không trả candidates: {error_msg}")
    candidate = data["candidates"][0]
    # Kiểm tra finish_reason
    finish_reason = candidate.get("finishReason", "")
    if finish_reason in ("SAFETY", "RECITATION"):
        raise ValueError(f"Gemini bị chặn bởi safety filter: {finish_reason}")
    raw = candidate["content"]["parts"][0]["text"]
    raw_clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{[\s\S]*\}", raw_clean)
        if m:
            return json.loads(m.group())
        raise ValueError(f"Không parse được JSON: {raw_clean[:200]}")


def format_telegram_message(matches_results: list, today: str) -> str:
    date_fmt = datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y")
    lines = [
        f"⚽ *DỰ ĐOÁN WORLD CUP 2026*",
        f"📅 {date_fmt} — {len(matches_results)} trận",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for i, item in enumerate(matches_results, 1):
        match = item["match"]
        result = item["result"]
        home, away = match["home"], match["away"]
        winner = result.get("winner", "?")
        score = result.get("scoreline", "?-?")
        conf = result.get("confidence", 0)
        h_pct = result.get("home_win_pct", 0)
        d_pct = result.get("draw_pct", 0)
        a_pct = result.get("away_win_pct", 0)
        analysis = result.get("analysis", "")
        factors = result.get("key_factors", [])

        if winner == home:
            winner_line = f"🏆 *{home}* thắng"
        elif winner == away:
            winner_line = f"🏆 *{away}* thắng"
        else:
            winner_line = "🤝 *Hòa*"

        filled = round(conf / 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)

        lines += [
            f"\n*{i}. {home} 🆚 {away}*",
            f"🕐 {match['time']} VN  |  {match['stage']}",
            f"",
            f"{winner_line}  ({score})",
            f"{bar} {conf}%",
            f"",
            f"📊 {home}: {round(h_pct)}%  |  Hòa: {round(d_pct)}%  |  {away}: {round(a_pct)}%",
        ]
        if factors:
            lines += ["", "📌 Yếu tố chính:"] + [f"  • {f}" for f in factors[:3]]
        if analysis:
            lines += ["", f"💬 _{analysis}_"]
        lines.append("━━━━━━━━━━━━━━━━━━")

    lines += ["", "🤖 _Phân tích bởi Gemini AI_",
              "_⚠️ Dự đoán tham khảo, bóng đá luôn có bất ngờ!_"]
    return "\n".join(lines)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }, timeout=15)
    resp.raise_for_status()
    print(f"✅ Đã gửi Telegram: {resp.json().get('ok')}")


def main():
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"🚀 Bắt đầu {datetime.now(VN_TZ).strftime('%H:%M')} ngày {today}")

    matches = get_todays_matches()
    if not matches:
        send_telegram(f"⚽ *WORLD CUP 2026*\n📅 {datetime.now(VN_TZ).strftime('%d/%m/%Y')}\n\n😴 Hôm nay không có trận đấu nào.")
        return

    print(f"📋 {len(matches)} trận đấu")
    results = []
    for match in matches:
        print(f"🔍 {match['home']} vs {match['away']}...")
        try:
            result = analyze_match_with_ai(match["home"], match["away"], match["stage"])
            results.append({"match": match, "result": result})
            print(f"  → {result.get('winner')} ({result.get('confidence')}%)")
        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
            results.append({"match": match, "result": {
                "winner": "Không xác định", "confidence": 50,
                "scoreline": "?-?", "home_win_pct": 33, "draw_pct": 34, "away_win_pct": 33,
                "analysis": "Không thể phân tích lúc này."}})

    send_telegram(format_telegram_message(results, today))
    print("🎉 Hoàn thành!")


if __name__ == "__main__":
    main()
