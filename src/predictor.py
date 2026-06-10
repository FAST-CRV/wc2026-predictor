import os
import json
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Vietnam timezone (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def get_todays_matches():
    """Scrape lịch thi đấu WC2026 hôm nay từ FlashScore"""
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"📅 Tìm trận đấu ngày: {today}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    # Thử API của football-data.org (free tier)
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        params = {"dateFrom": today, "dateTo": today, "status": "SCHEDULED,TIMED,IN_PLAY"}
        resp = requests.get(url, headers={**headers, "X-Auth-Token": ""}, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            matches = []
            for m in data.get("matches", []):
                home = m["homeTeam"]["name"]
                away = m["awayTeam"]["name"]
                utc_time = m.get("utcDate", "")
                try:
                    dt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                    local_time = dt.astimezone(VN_TZ).strftime("%H:%M")
                except Exception:
                    local_time = "TBD"
                matches.append({
                    "home": home,
                    "away": away,
                    "time": local_time,
                    "stage": m.get("stage", "GROUP_STAGE"),
                })
            if matches:
                return matches
    except Exception as e:
        print(f"⚠️ football-data.org lỗi: {e}")

    # Fallback: scrape SofaScore
    try:
        url = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            matches = []
            for event in data.get("events", []):
                tournament = event.get("tournament", {}).get("name", "")
                if "world cup" in tournament.lower() or "FIFA" in tournament:
                    home = event["homeTeam"]["name"]
                    away = event["awayTeam"]["name"]
                    ts = event.get("startTimestamp", 0)
                    if ts:
                        dt = datetime.fromtimestamp(ts, tz=VN_TZ)
                        local_time = dt.strftime("%H:%M")
                    else:
                        local_time = "TBD"
                    matches.append({
                        "home": home,
                        "away": away,
                        "time": local_time,
                        "stage": "World Cup 2026",
                    })
            if matches:
                return matches
    except Exception as e:
        print(f"⚠️ SofaScore lỗi: {e}")

    # Fallback hardcode lịch WC2026 vòng bảng (11/6 - 3/7/2026)
    print("⚠️ Dùng lịch hardcode WC2026")
    return get_hardcoded_schedule(today)


def get_hardcoded_schedule(today: str):
    """Lịch thi đấu WC2026 vòng bảng hardcode (các trận tiêu biểu)"""
    schedule = {
        # Ngày khai mạc
        "2026-06-11": [{"home": "Mexico", "away": "Chile",       "time": "22:00", "stage": "Group A"},
                       {"home": "USA",    "away": "Canada",      "time": "01:00", "stage": "Group B"}],
        "2026-06-12": [{"home": "Brazil", "away": "Mexico",      "time": "22:00", "stage": "Group D"},
                       {"home": "Argentina","away":"Ecuador",    "time": "02:00", "stage": "Group A"}],
        "2026-06-13": [{"home": "France", "away": "Uruguay",     "time": "22:00", "stage": "Group E"},
                       {"home": "Germany","away":"Japan",        "time": "02:00", "stage": "Group C"}],
        "2026-06-14": [{"home": "Spain",  "away": "Morocco",     "time": "22:00", "stage": "Group H"},
                       {"home": "England","away":"Iran",         "time": "02:00", "stage": "Group F"}],
        "2026-06-15": [{"home": "Portugal","away":"South Korea", "time": "22:00", "stage": "Group G"},
                       {"home": "Netherlands","away":"Senegal",  "time": "02:00", "stage": "Group I"}],
        "2026-06-16": [{"home": "Italy",  "away": "Belgium",     "time": "02:00", "stage": "Group J"},
                       {"home": "Croatia","away":"Colombia",     "time": "22:00", "stage": "Group K"}],
        "2026-06-17": [{"home": "Argentina","away":"Saudi Arabia","time":"22:00", "stage": "Group B"},
                       {"home": "Brazil", "away": "Japan",       "time": "02:00", "stage": "Group D"}],
        "2026-06-18": [{"home": "France", "away": "Germany",     "time": "22:00", "stage": "Group C"},
                       {"home": "Spain",  "away": "Netherlands", "time": "02:00", "stage": "Group H"}],
        "2026-06-19": [{"home": "England","away":"USA",          "time": "22:00", "stage": "Group F"},
                       {"home": "Portugal","away":"Uruguay",     "time": "02:00", "stage": "Group E"}],
        "2026-06-20": [{"home": "Vietnam","away":"Saudi Arabia", "time": "22:00", "stage": "Group K"},
                       {"home": "Australia","away":"Iran",       "time": "02:00", "stage": "Group L"}],
    }
    return schedule.get(today, [])


def analyze_match_with_ai(home: str, away: str, stage: str) -> dict:
    """Gọi Claude API để phân tích và dự đoán trận đấu"""
    prompt = f"""Bạn là chuyên gia phân tích bóng đá World Cup 2026.

Trận đấu: {home} vs {away}
Giai đoạn: {stage}

Hãy phân tích và dự đoán kết quả. Trả lời CHỈ bằng JSON hợp lệ (không markdown, không backtick):
{{
  "winner": "tên đội thắng hoặc 'Hòa'",
  "confidence": số từ 50 đến 82,
  "scoreline": "ví dụ 2-1",
  "home_win_pct": số,
  "draw_pct": số,
  "away_win_pct": số,
  "key_factors": ["yếu tố 1", "yếu tố 2", "yếu tố 3"],
  "star_players": ["cầu thủ ngôi sao đội nhà", "cầu thủ ngôi sao đội khách"],
  "analysis": "2-3 câu phân tích ngắn gọn bằng tiếng Việt về phong độ, chiến thuật, lý do dự đoán"
}}"""

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]

    # Parse JSON
    raw_clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{[\s\S]*\}", raw_clean)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Không parse được JSON: {raw_clean[:200]}")


def format_telegram_message(matches_results: list, today: str) -> str:
    """Format tin nhắn Telegram đẹp"""
    date_fmt = datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y")
    lines = [
        f"⚽ *DỰ ĐOÁN WORLD CUP 2026*",
        f"📅 {date_fmt} — {len(matches_results)} trận",
        "━━━━━━━━━━━━━━━━━━",
    ]

    for i, item in enumerate(matches_results, 1):
        match = item["match"]
        result = item["result"]
        home = match["home"]
        away = match["away"]
        time = match["time"]
        stage = match["stage"]

        winner = result.get("winner", "?")
        score = result.get("scoreline", "?-?")
        conf = result.get("confidence", 0)
        h_pct = result.get("home_win_pct", 0)
        d_pct = result.get("draw_pct", 0)
        a_pct = result.get("away_win_pct", 0)
        analysis = result.get("analysis", "")
        factors = result.get("key_factors", [])

        # Xác định winner emoji
        if winner == home:
            winner_line = f"🏆 *{home}* thắng"
        elif winner == away:
            winner_line = f"🏆 *{away}* thắng"
        else:
            winner_line = "🤝 *Hòa*"

        # Confidence bar
        filled = round(conf / 10)
        bar = "🟩" * filled + "⬜" * (10 - filled)

        lines += [
            f"\n*{i}. {home} 🆚 {away}*",
            f"🕐 {time} VN  |  {stage}",
            f"",
            f"{winner_line}  ({score})",
            f"{bar} {conf}%",
            f"",
            f"📊 {home}: {round(h_pct)}%  |  Hòa: {round(d_pct)}%  |  {away}: {round(a_pct)}%",
        ]

        if factors:
            lines.append(f"")
            lines.append(f"📌 Yếu tố chính:")
            for f in factors[:3]:
                lines.append(f"  • {f}")

        if analysis:
            lines.append(f"")
            lines.append(f"💬 _{analysis}_")

        lines.append("━━━━━━━━━━━━━━━━━━")

    lines += [
        "",
        "🤖 _Phân tích bởi Claude AI_",
        "_⚠️ Dự đoán tham khảo, bóng đá luôn có bất ngờ!_",
    ]
    return "\n".join(lines)


def send_telegram(message: str):
    """Gửi tin nhắn qua Telegram Bot API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    print(f"✅ Đã gửi Telegram: {resp.json().get('ok')}")


def main():
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"🚀 Bắt đầu chạy lúc {datetime.now(VN_TZ).strftime('%H:%M')} ngày {today}")

    matches = get_todays_matches()

    if not matches:
        msg = f"⚽ *WORLD CUP 2026*\n📅 {datetime.now(VN_TZ).strftime('%d/%m/%Y')}\n\n😴 Hôm nay không có trận đấu nào."
        send_telegram(msg)
        print("Không có trận đấu hôm nay.")
        return

    print(f"📋 Tìm thấy {len(matches)} trận đấu")

    results = []
    for match in matches:
        print(f"🔍 Phân tích: {match['home']} vs {match['away']}...")
        try:
            result = analyze_match_with_ai(match["home"], match["away"], match["stage"])
            results.append({"match": match, "result": result})
            print(f"  → Dự đoán: {result.get('winner')} ({result.get('confidence')}%)")
        except Exception as e:
            print(f"  ❌ Lỗi phân tích: {e}")
            results.append({
                "match": match,
                "result": {"winner": "Không xác định", "confidence": 50,
                           "scoreline": "?-?", "home_win_pct": 33,
                           "draw_pct": 34, "away_win_pct": 33,
                           "analysis": "Không thể phân tích lúc này."}
            })

    message = format_telegram_message(results, today)
    send_telegram(message)
    print("🎉 Hoàn thành!")


if __name__ == "__main__":
    main()
