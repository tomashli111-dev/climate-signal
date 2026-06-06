import feedparser
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

# ─────────────────────────────────────────────
# CONFIGURATION — add or remove feeds here
# ─────────────────────────────────────────────
RSS_FEEDS = [
    # Right-leaning / sceptic
    {"source": "The Spectator",       "url": "https://www.spectator.co.uk/feed/"},
    {"source": "GB News",             "url": "https://www.gbnews.com/feeds/news.rss"},
    {"source": "Daily Mail",          "url": "https://www.dailymail.co.uk/news/environment/index.rss"},

    # Centre
    {"source": "BBC Environment",     "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"source": "Reuters",             "url": "https://feeds.reuters.com/reuters/environment"},
    {"source": "Sky News",            "url": "https://feeds.skynews.com/feeds/rss/environment.xml"},

    # Centre-left
    {"source": "The Guardian",        "url": "https://www.theguardian.com/environment/climate-crisis/rss"},
    {"source": "The Independent",     "url": "https://www.independent.co.uk/climate-change/rss"},

    # Specialist / activist
    {"source": "Carbon Brief",        "url": "https://www.carbonbrief.org/feed/"},
    {"source": "Climate Home News",   "url": "https://www.climatechangenews.com/feed/"},

    # Science
    {"source": "Yale Environment 360","url": "https://e360.yale.edu/feed.xml"},
    {"source": "NASA Climate",        "url": "https://climate.nasa.gov/news/rss.xml"},
]

MAX_ARTICLES_PER_FEED = 5   # how many articles to pull per source
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────
# FETCH ARTICLES FROM RSS
# ─────────────────────────────────────────────
def fetch_articles():
    articles = []
    for feed_config in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_config["url"])
            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary
                summary = re.sub(r'<[^>]+>', '', summary).strip()
                summary = summary[:800]  # cap length

                pub_date = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6]).strftime("%-d %b %Y")

                if title and url:
                    articles.append({
                        "source": feed_config["source"],
                        "title": title,
                        "url": url,
                        "raw_summary": summary,
                        "date": pub_date,
                    })
            print(f"✓ {feed_config['source']}: {min(len(feed.entries), MAX_ARTICLES_PER_FEED)} articles")
        except Exception as e:
            print(f"✗ {feed_config['source']}: {e}")
    return articles

# ─────────────────────────────────────────────
# CALL CLAUDE API FOR SUMMARY + TONE
# ─────────────────────────────────────────────
def analyse_article(article):
    if not ANTHROPIC_API_KEY:
        # No API key yet — return placeholder
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral"
        }

    prompt = f"""You are analysing a climate news article for a media monitoring tool.

Article title: {article['title']}
Article excerpt: {article['raw_summary']}
Source: {article['source']}

Please respond with ONLY a JSON object in this exact format:
{{
  "summary": "A 2-3 sentence plain-English summary of the article for a general audience.",
  "tone": "one of: alarmist, hopeful, neutral, solutions, political"
}}

Tone definitions:
- alarmist: urgent crisis framing, fear-led language, emphasises catastrophe
- hopeful: focuses on progress, positive outcomes, optimism
- neutral: factual and measured, no strong emotional framing
- solutions: centres on fixes — technology, policy, behaviour change
- political: focuses on policy debate, blame, partisan framing

Respond only with the JSON, no other text."""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            }
        )

        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
            text = data["content"][0]["text"].strip()
            # Strip markdown fences if present
            text = re.sub(r'^```json\s*|\s*```$', '', text).strip()
            result = json.loads(text)
            return {
                "summary": result.get("summary", ""),
                "tone": result.get("tone", "neutral")
            }
    except Exception as e:
        print(f"  API error for '{article['title'][:40]}...': {e}")
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral"
        }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("Climate Signal — daily build")
    print("=" * 40)

    print("\nFetching RSS feeds...")
    raw_articles = fetch_articles()
    print(f"\nTotal articles fetched: {len(raw_articles)}")

    if not ANTHROPIC_API_KEY:
        print("\n⚠ No ANTHROPIC_API_KEY found — skipping AI analysis, using raw summaries")
    else:
        print("\nRunning AI analysis...")

    processed = []
    for i, article in enumerate(raw_articles):
        print(f"  [{i+1}/{len(raw_articles)}] {article['title'][:55]}...")
        analysis = analyse_article(article)
        if ANTHROPIC_API_KEY:
            time.sleep(0.3)  # small delay to be polite to the API

        processed.append({
            "title": article["title"],
            "url": article["url"],
            "source": article["source"],
            "date": article["date"],
            "summary": analysis["summary"],
            "tone": analysis["tone"],
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": processed
    }

    out_path = os.path.join(os.path.dirname(__file__), "docs", "articles.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Done! {len(processed)} articles written to docs/articles.json")

if __name__ == "__main__":
    main()
