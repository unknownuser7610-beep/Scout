import os
import time
import json
import html
import feedparser
import requests

FEEDS = [
    # 1. Google News: Kerala Macro Bottlenecks (Senior care, NRI property, labor shortages)
    "https://news.google.com/rss/search?q=Kerala+(%22shortage%22+OR+%22elderly+care%22+OR+%22labor+shortage%22+OR+%22NRI+property%22)+when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    
    # 2. Google News: Kochi & Trivandrum Urban Service Failures
    "https://news.google.com/rss/search?q=(Kochi+OR+Trivandrum)+(%22water+crisis%22+OR+%22waste+management%22+OR+%22domestic+help%22+OR+%22contractor%22)+when:3d&hl=en-IN&gl=IN&ceid=IN:en",
    
    # 3. Reddit r/Kerala: High-intent solution-seeking & NRI logistics
    "https://www.reddit.com/r/Kerala/search.rss?q=recommend+OR+%22looking+for%22+OR+%22property+management%22+OR+%22elderly%22&sort=new",
    
    # 4. Reddit r/Kochi: Service discovery and contractor bottlenecks
    "https://www.reddit.com/r/Kochi/search.rss?q=trustworthy+OR+reliable+OR+%22anyone+know%22+OR+contractor&sort=new",
    
    # 5. Reddit r/Trivandrum: Commercial recommendations & service hiring
    "https://www.reddit.com/r/Trivandrum/search.rss?q=service+OR+recommendation+OR+cost+OR+hiring&sort=new"
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT")

# Custom User-Agent prevents Reddit & Google from blocking GitHub Actions runners
HEADERS = {"User-Agent": "KeralaScoutEngine/2.0 (Commercial Opportunity Scanner)"}

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
            print(f"Telegram API error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Telegram connection error: {e}")

def evaluate_post(title, summary, link):
    prompt = f"""
    You are an unforgiving venture researcher evaluating business opportunities specifically for Kerala, India.
    Analyze this item:
    Title: {title}
    Content: {summary}

    Diagnostic Filters:
    1. High-friction commercial pain point (not everyday venting, politics, gossip, or one-off complaints)?
    2. Kerala viability (aging demographic, high NRI remittances, monsoon seasonality, labor/union constraints)?
    3. Who signs the check (Gulf NRIs, villa associations, local SMEs, high-net-worth families)?
    4. Can a founder test this in 14 days without heavy upfront machinery or capital expenditure?
    5. What is the single biggest operational flaw?

    Return ONLY raw JSON (no markdown formatting, no backticks):
    {{
      "is_viable": true or false,
      "domain": "Domain Name",
      "core_problem": "Short clinical problem summary",
      "target_payer": "Exact persona with money",
      "unfair_kerala_advantage": "Kerala-specific market edge",
      "zero_capital_mvp": "2-week manual test plan",
      "fatal_risk": "Biggest failure risk",
      "commercial_score": 1 to 10
    }}
    Be strict. If the post is an emotional rant, gossip, or economically unfeasible, set "is_viable" to false.
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
    print("Starting multi-source Kerala Scout sweep...")
    send_telegram_raw("🚀 <b>Kerala Scout pipeline has started running!</b>")
    
    scouted_count = 0
    qualified_count = 0

    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url, request_headers=HEADERS)
        print(f"Feed fetched: {len(parsed.entries)} entries.")
        
        # Check top 8 entries per feed across both news and Reddit
        for entry in parsed.entries[:8]:
            scouted_count += 1
            summary = getattr(entry, "summary", "")
            analysis = evaluate_post(entry.title, summary, entry.link)
            
            if analysis:
                score = analysis.get("commercial_score", 0)
                is_viable = analysis.get("is_viable", False)
                print(f"[{score}/10] Viable: {is_viable} | {entry.title[:45]}")
                
                # Strict 7+ cutoff preserved
                if is_viable and score >= 7:
                    send_telegram_alert(entry.title, entry.link, analysis)
                    qualified_count += 1
            
            # Safe sleep window to respect Gemini Flash tier quotas
            time.sleep(1.5)

    if qualified_count == 0:
        empty_msg = (
            f"🔍 <b>Kerala Scout Sweep Complete</b>\n\n"
            f"Evaluated <b>{scouted_count}</b> entries across Google News, r/Kerala, r/Kochi, and r/Trivandrum.\n"
            f"No commercial opportunities passed the strict 7/10 diagnostic this run."
        )
        send_telegram_raw(empty_msg)

    print(f"Sweep complete. Evaluated: {scouted_count}, Qualified (Score >= 7): {qualified_count}")

if __name__ == "__main__":
    main()
