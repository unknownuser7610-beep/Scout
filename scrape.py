import os
import time
import json
import html
import feedparser
import requests

FEEDS = [
    "https://www.reddit.com/r/Kerala/search.rss?q=problem+OR+struggle+OR+terrible+OR+service+OR+parents&sort=new",
    "https://www.reddit.com/r/Kochi/search.rss?q=issue+OR+broken+OR+scam+OR+expensive+OR+maid&sort=new",
    "https://www.reddit.com/r/Trivandrum/search.rss?q=need+OR+frustrating+OR+waste&sort=new"
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT")

# Reddit requires a custom User-Agent to avoid HTTP 429/403 blocks on cloud IPs
HEADERS = {"User-Agent": "KeralaScoutBot/1.0 (by /u/kerala_scout)"}

def send_telegram_raw(html_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"Telegram error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Telegram connection error: {e}")

def evaluate_post(title, summary, link):
    prompt = f"""
    You are an unforgiving venture researcher evaluating business opportunities specifically for Kerala, India.
    Analyze this user post:
    Title: {title}
    Content: {summary}

    Diagnostic Filters:
    1. High-friction commercial pain point (not everyday venting/politics/relationship issues)?
    2. Kerala viability (aging demographic, high NRI remittances, monsoon seasonality, labor/union constraints)?
    3. Who signs the check (Gulf NRIs, villa associations, local businesses)?
    4. Can a founder test this in 14 days without buying heavy machinery?
    5. What is the single biggest operational flaw?

    Return ONLY raw JSON (no markdown fences, no backticks):
    {{
      "is_viable": true,
      "domain": "Domain Name",
      "core_problem": "Short problem summary",
      "target_payer": "Target persona",
      "unfair_kerala_advantage": "Kerala edge",
      "zero_capital_mvp": "2-week test plan",
      "fatal_risk": "Biggest failure risk",
      "commercial_score": 1
    }}
    Be strict. If the post is an emotional rant, gossip, or unfeasible, set "is_viable" to false.
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
        print(f"Evaluation error for '{title[:30]}': {e}")
        return None

def send_telegram_alert(post_title, post_link, analysis):
    domain = html.escape(str(analysis.get('domain', 'N/A')))
    target = html.escape(str(analysis.get('target_payer', 'N/A')))
    problem = html.escape(str(analysis.get('core_problem', 'N/A')))
    advantage = html.escape(str(analysis.get('unfair_kerala_advantage', 'N/A')))
    mvp = html.escape(str(analysis.get('zero_capital_mvp', 'N/A')))
    risk = html.escape(str(analysis.get('fatal_risk', 'N/A')))
    score = analysis.get('commercial_score', 0)

    msg = (
        f"🌴 <b>Kerala Market Opportunity</b> ({score}/10)\n\n"
        f"📂 <b>Domain:</b> {domain}\n"
        f"🎯 <b>Target Payer:</b> {target}\n\n"
        f"⚠️ <b>Problem:</b> {problem}\n"
        f"📍 <b>Kerala Edge:</b> {advantage}\n"
        f"🛠 <b>2-Week MVP:</b> {mvp}\n"
        f"🚨 <b>Fatal Risk:</b> {risk}\n\n"
        f"🔗 <a href='{post_link}'>View Source Discussion</a>"
    )
    send_telegram_raw(msg)

def main():
    print("Sending pipeline start alert...")
    send_telegram_raw("🚀 <b>Kerala Scout pipeline has started running!</b>")
    
    scouted_count = 0
    qualified_count = 0

    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url, request_headers=HEADERS)
        print(f"Feed fetched: {len(parsed.entries)} entries found.")
        
        for entry in parsed.entries[:5]:  # Sweeps top 5 recent posts per feed
            scouted_count += 1
            summary = getattr(entry, "summary", "")
            analysis = evaluate_post(entry.title, summary, entry.link)
            
            if analysis:
                score = analysis.get("commercial_score", 0)
                is_viable = analysis.get("is_viable", False)
                print(f"[{score}/10] Viable: {is_viable} | {entry.title[:45]}")
                
                if is_viable and score >= 6:
                    send_telegram_alert(entry.title, entry.link, analysis)
                    qualified_count += 1
            time.sleep(4)

    # If no posts met the criteria, send an explicit completion summary
    if qualified_count == 0:
        empty_msg = (
            f"🔍 <b>Kerala Scout Sweep Complete</b>\n\n"
            f"Evaluated <b>{scouted_count}</b> posts across r/Kerala, r/Kochi, and r/Trivandrum.\n"
            f"No viable commercial opportunities scored 6/10 or above this run."
        )
        send_telegram_raw(empty_msg)

    print(f"Run finished. Scouted: {scouted_count}, Qualified: {qualified_count}")

if __name__ == "__main__":
    main()
