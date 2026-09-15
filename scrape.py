import os
import time
import json
import feedparser
import requests

FEEDS = [
    "https://www.reddit.com/r/Kerala/search.rss?q=problem+OR+struggle+OR+terrible+OR+service+OR+parents&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/Kochi/search.rss?q=issue+OR+broken+OR+scam+OR+expensive+OR+maid&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/Trivandrum/search.rss?q=need+OR+frustrating+OR+waste&sort=new&restrict_sr=1"
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT")

# Headers to avoid bot blocks when scraping RSS
HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}

def evaluate_post(title, summary, link):
    prompt = f"""
    You are an unforgiving venture researcher evaluating business opportunities specifically for Kerala, India.
    Analyze this post:
    Title: {title}
    Content: {summary}

    Diagnostic Filters:
    1. Pain Severity: Is this a genuine commercial problem people will pay money to solve, or just everyday venting/politics/relationship talk?
    2. Kerala Viability: Will local conditions (monsoon seasonality, union/labor issues, high NRI diaspora, aging population) break this or enable it?
    3. Unit Economics: Who actually signs the check (Gulf NRIs, resident societies, local businesses)?
    4. Asset-Light MVP: Can a founder test demand in 14 days without buying heavy machinery?
    5. Fatal Flaws: What is the #1 reason this business will fail within 6 months?

    Return ONLY a raw JSON object (no markdown, no backticks):
    {{
      "is_viable": true or false,
      "category": "Senior Care / Property Stewardship / Waste / Agri / B2B Service",
      "core_problem": "One-line clinical summary of the true commercial bottleneck",
      "target_payer": "Exact persona with money",
      "unfair_kerala_advantage": "Why this works specifically in Kerala",
      "zero_capital_mvp": "Specific 2-week plan to test demand manually",
      "fatal_risk": "The biggest operational bottleneck or why customers churn",
      "commercial_score": 1 to 10
    }}
    Be strict. If it is casual gossip, an emotional rant, or unfeasible, set "is_viable" to false.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
    }
    
    try:
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()
        result_text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Evaluation error: {e}")
        return None

def send_telegram_alert(post_title, post_link, analysis):
    msg = (
        f"🌴 *High-Scoring Kerala Business Gap* ({analysis.get('commercial_score')}/10)\n\n"
        f"📂 *Domain:* {analysis.get('category')}\n"
        f"🎯 *Target Payer:* {analysis.get('target_payer')}\n\n"
        f"⚠️ *Core Problem:* {analysis.get('core_problem')}\n"
        f"📍 *Kerala Edge:* {analysis.get('unfair_kerala_advantage')}\n"
        f"🛠 *2-Week MVP:* {analysis.get('zero_capital_mvp')}\n"
        f"🚨 *Fatal Risk:* {analysis.get('fatal_risk')}\n\n"
        f"🔗 [View Source Discussion]({post_link})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload, timeout=10)

def main():
    print("Sweeping Kerala discussion feeds...")
    for feed_url in FEEDS:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=15)
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:3]:
                analysis = evaluate_post(entry.title, entry.summary, entry.link)
                if analysis and analysis.get("is_viable") is True and analysis.get("commercial_score", 0) >= 7:
                    send_telegram_alert(entry.title, entry.link, analysis)
                time.sleep(4)
        except Exception as err:
            print(f"Feed fetch failed for {feed_url}: {err}")

if __name__ == "__main__":
    main()
