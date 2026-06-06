import feedparser
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
RSS_FEEDS = [
    # Right-leaning / sceptic
    {"source": "The Spectator",    "url": "https://www.spectator.co.uk/feed/",                                "max": 50},
    {"source": "GB News",          "url": "https://www.gbnews.com/feeds/news.rss",                            "max": 50},
    {"source": "Daily Mail",       "url": "https://www.dailymail.co.uk/sciencetech/index.rss",                "max": 50},
    {"source": "The Sun",          "url": "https://www.thesun.co.uk/feed/",                                   "max": 50},
    {"source": "The Telegraph",    "url": "https://www.telegraph.co.uk/rss.xml",                              "max": 50},
    {"source": "The Express",      "url": "https://www.express.co.uk/posts/rss",                              "max": 50},

    # Centre
    {"source": "BBC Environment",  "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",    "max": 20},
    {"source": "Sky News",         "url": "https://feeds.skynews.com/feeds/rss/home.xml",                     "max": 50},
    {"source": "Evening Standard", "url": "https://www.standard.co.uk/news/rss",                              "max": 50},
    {"source": "The i",            "url": "https://inews.co.uk/feed",                                         "max": 20},

    # Centre-left
    {"source": "The Guardian",     "url": "https://www.theguardian.com/environment/climate-crisis/rss",       "max": 20},
    {"source": "The Independent",  "url": "https://www.independent.co.uk/rss",                                "max": 50},
    {"source": "The Mirror",       "url": "https://www.mirror.co.uk/?service=rss",                            "max": 50},
    {"source": "Channel 4 News",   "url": "https://www.channel4.com/news/feed",                               "max": 50},
]

ROLLING_DAYS = 7
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TOPICS = [
    "Net Zero & Climate Policy",
    "Wind & Solar Energy",
    "Oil, Gas & Fossil Fuels",
    "Electric Vehicles & Transport",
    "Nature & Biodiversity",
    "Extreme Weather & Climate Science",
    "Pollution & Environment",
    "International Climate Politics",
    "Other",
]

# ─────────────────────────────────────────────
# KEYWORD FILTER
# ─────────────────────────────────────────────
TIER1 = [
    # Core climate
    'climate change', 'climate crisis', 'climate emergency', 'climate action',
    'climate policy', 'climate summit', 'climate target', 'climate model',
    'climate finance', 'climate activist', 'climate sceptic', 'climate skeptic',
    'climate denier', 'climate alarmist', 'climate hysteria', 'climate cult',
    'climate agenda', 'climate lobby', 'climate litigation', 'climate lawsuit',
    'climate science', 'climate data', 'climate report',
    'global warming', 'greenhouse gas', 'greenhouse effect',
    'carbon emissions', 'carbon footprint', 'carbon capture', 'carbon offset',
    'carbon tax', 'carbon budget', 'carbon neutral', 'carbon dioxide',
    'carbon price', 'carbon market', 'carbon border', 'carbon tariff',
    'stranded assets', 'scope 3 emissions', 'methane emissions', 'co2 emissions',
    'net zero', 'decarbonisation', 'decarbonization',

    # Policy & agreements
    'paris agreement', 'cop29', 'cop30', 'cop31', 'ipcc', 'unfccc',
    'emissions trading', 'emissions target', 'emissions reduction',
    'just transition', 'green new deal', 'loss and damage fund',
    'nature-based solutions', 'biodiversity net gain', 'environment act',
    'seventh carbon budget', 'sixth carbon budget', 'clean power 2030',
    'great british energy', 'energy security bill', 'climate change committee',
    'net zero strategy', 'green finance',

    # Energy
    'fossil fuel', 'renewable energy', 'clean energy', 'energy transition',
    'offshore wind', 'onshore wind', 'wind farm', 'wind turbine', 'wind power',
    'solar power', 'solar panel', 'solar farm', 'solar energy',
    'green hydrogen', 'hydrogen fuel', 'tidal power', 'tidal energy',
    'nuclear energy', 'nuclear power', 'battery storage', 'energy storage',
    'grid capacity', 'north sea oil', 'north sea gas', 'north sea licence',
    'rosebank oilfield', 'cambo oilfield', 'fracking', 'coal power', 'coal mine',
    'coal fired', 'oil industry', 'oil drilling', 'gas drilling', 'gas pipeline',
    'oil spill', 'energy poverty', 'fuel poverty',
    'green levies', 'green tax', 'wind subsidy', 'solar subsidy',

    # Transport
    'electric vehicle', 'electric car', 'ev charging', 'ev mandate',
    'petrol ban', 'diesel ban', 'boiler ban', 'boiler upgrade', 'heat pump',
    'ulez', 'low emission zone', 'war on motorists', 'war on drivers',
    'ban on petrol', 'ban on diesel', 'zero emission vehicle',

    # Nature & biodiversity
    'biodiversity', 'species extinction', 'habitat loss', 'deforestation',
    'reforestation', 'rewilding', 'ocean acidification', 'sea level rise',
    'arctic ice', 'arctic melt', 'glacier retreat', 'permafrost',
    'coral reef', 'coral bleaching', 'marine protected area', 'nature recovery',
    'wildlife corridor', 'species decline', 'bee population', 'insect population',
    'endangered species', 'habitat destruction', 'rainforest destruction',
    'mangrove', 'kelp forest', 'peatland', 'wetlands loss',

    # Pollution
    'plastic pollution', 'microplastics', 'water pollution', 'toxic waste',
    'sewage dumping', 'river pollution', 'air pollution', 'particulate matter',
    'nitrogen dioxide', 'pm2.5', 'chemical pollution',

    # Sceptic / tabloid framing
    'green blob', 'eco zealot', 'eco madness', 'green madness',
    'net zero madness', 'net zero cost', 'net zero burden', 'net zero bill',
    'green ideology', 'green obsession', 'green targets', 'eco activist',
    'extinction rebellion', 'just stop oil', 'insulate britain',
    'greenwashing', 'wind farm backlash', 'solar farm backlash',

    # Climate science & reporting
    'hottest year', 'hottest ever', 'record temperature', 'record heat',
    'extreme weather event', 'ipcc report', 'global temperature',
    'temperature record', 'sea level', 'el nino', 'el niño',
    'sea defences', 'environment agency', 'natural england',

    # UK specific policy
    'climate change committee', 'carbon budget uk',
    'north sea energy', 'clean power target',
]

TIER2 = [
    'flooding', 'flash flood', 'drought', 'heatwave', 'heat stress',
    'wildfire', 'water scarcity', 'storm surge',
    'energy bills', 'energy costs', 'energy crisis', 'energy price',
    'electricity price', 'heating costs',
    'sustainability', 'sustainable development',
    'circular economy', 'sustainable agriculture',
    'regenerative farming', 'soil health',
    'ecosystem', 'coal industry', 'gas leak', 'air quality',
    'el nino', 'flood risk',
]

def is_relevant(article):
    text = (
        article.get('title', '') + ' ' +
        article.get('raw_rss', '') + ' ' +
        article.get('raw_content', '')
    ).lower()
    if any(kw in text for kw in TIER1):
        return True
    tier2_matches = sum(1 for kw in TIER2 if kw in text)
    if tier2_matches >= 2:
        return True
    return False

# ─────────────────────────────────────────────
# FETCH META DESCRIPTION
# ─────────────────────────────────────────────
def fetch_meta_description(url):
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ClimateSignalBot/1.0)',
            'Accept': 'text/html',
        })
        with urlopen(req, timeout=10) as response:
            html = response.read(50000).decode('utf-8', errors='ignore')
        og = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if og:
            return og.group(1).strip()
        meta = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if meta:
            return meta.group(1).strip()
        return ""
    except Exception:
        return ""

# ─────────────────────────────────────────────
# LOAD EXISTING ARCHIVE
# ─────────────────────────────────────────────
def load_existing(out_path):
    try:
        with open(out_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('articles', [])
    except Exception:
        return []

# ─────────────────────────────────────────────
# FETCH ARTICLES FROM RSS
# ─────────────────────────────────────────────
def fetch_articles():
    articles = []
    now = datetime.now(timezone.utc)

    for feed_config in RSS_FEEDS:
        max_articles = feed_config.get("max", 20)
        try:
            feed = feedparser.parse(feed_config["url"])
            count = 0
            for entry in feed.entries[:max_articles]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "")

                raw_rss = entry.get("summary", entry.get("description", ""))
                raw_rss = re.sub(r'<[^>]+>', '', raw_rss).strip()
                raw_rss = raw_rss[:800]

                raw_content = ""
                if hasattr(entry, "content") and entry.content:
                    raw_content = entry.content[0].get("value", "")
                    raw_content = re.sub(r'<[^>]+>', '', raw_content).strip()
                    raw_content = raw_content[:1500]

                raw_summary = raw_content if len(raw_content) > len(raw_rss) else raw_rss

                pub_date_str = ""
                pub_date_dt = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        pub_date_str = pub_date_dt.strftime("%-d %b %Y")
                    except Exception:
                        pass

                if pub_date_dt and (now - pub_date_dt).days > ROLLING_DAYS:
                    continue

                if title and url:
                    articles.append({
                        "source": feed_config["source"],
                        "title": title,
                        "url": url,
                        "raw_summary": raw_summary,
                        "raw_rss": raw_rss,
                        "raw_content": raw_content,
                        "date": pub_date_str,
                        "pub_date_iso": pub_date_dt.isoformat() if pub_date_dt else "",
                    })
                    count += 1

            print(f"✓ {feed_config['source']}: {count} articles (within {ROLLING_DAYS} days)")
        except Exception as e:
            print(f"✗ {feed_config['source']}: {e}")

    filtered = []
    for article in articles:
        if is_relevant(article):
            filtered.append(article)
        else:
            print(f"  ✗ Filtered out: {article['title'][:60]}")

    print(f"After keyword filter: {len(filtered)}/{len(articles)} articles kept")
    return filtered

# ─────────────────────────────────────────────
# CLAUDE API
# ─────────────────────────────────────────────
def analyse_article(article):
    available_text = (
        article.get('raw_rss', '') + ' ' +
        article.get('raw_content', '') + ' ' +
        article.get('meta_description', '')
    ).strip()

    if not ANTHROPIC_API_KEY:
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral",
            "topic": "Other",
            "low_confidence": len(available_text) < 50,
        }

    low_confidence = len(available_text) < 50
    if low_confidence:
        return {
            "summary": "Insufficient source data for a reliable summary — click to read the full article.",
            "tone": "neutral",
            "topic": "Other",
            "low_confidence": True,
        }

    source_data = f"Title: {article['title']}\nSource: {article['source']}\n"
    if article.get('raw_rss'):
        source_data += f"RSS excerpt: {article['raw_rss']}\n"
    if article.get('raw_content') and article['raw_content'] != article.get('raw_rss'):
        source_data += f"Full RSS content: {article['raw_content']}\n"
    if article.get('meta_description') and article['meta_description'] not in (article.get('raw_rss',''), article.get('raw_content','')):
        source_data += f"Page description: {article['meta_description']}\n"

    topics_list = "\n".join(f"- {t}" for t in TOPICS)

    prompt = f"""You are analysing a climate and environment news article for a media monitoring tool.

Here is all available data about this article:
{source_data}

Important: Base your analysis ONLY on the information provided above. Do not add details, statistics, or context not present in the source data. If the source data is limited, keep the summary brief and factual.

Please respond with ONLY a JSON object in this exact format:
{{
  "summary": "A 2-3 sentence plain-English summary based strictly on the source data above.",
  "tone": "one of: alarmist, hopeful, neutral, solutions, political",
  "topic": "one of the topics listed below"
}}

Tone definitions:
- alarmist: urgent crisis framing, fear-led language, emphasises catastrophe
- hopeful: focuses on progress, positive outcomes, optimism
- neutral: factual and measured, no strong emotional framing
- solutions: centres on fixes — technology, policy, behaviour change
- political: focuses on policy debate, blame, partisan framing

Topic options (pick the single most relevant):
{topics_list}

Respond only with the JSON, no other text."""

    try:
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 400,
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
            text = re.sub(r'^```json\s*|\s*```$', '', text).strip()
            result = json.loads(text)
            return {
                "summary": result.get("summary", ""),
                "tone": result.get("tone", "neutral"),
                "topic": result.get("topic", "Other"),
                "low_confidence": False,
            }
    except Exception as e:
        print(f"  API error for '{article['title'][:40]}...': {e}")
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral",
            "topic": "Other",
            "low_confidence": len(available_text) < 50,
        }

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("Climate Signal — daily build")
    print("=" * 40)

    out_path = os.path.join(os.path.dirname(__file__), "docs", "articles.json")

    existing = load_existing(out_path)
    existing_urls = {a['url'] for a in existing}
    print(f"\nExisting archive: {len(existing)} articles")

    cutoff = datetime.now(timezone.utc) - timedelta(days=ROLLING_DAYS)
    existing = [
        a for a in existing
        if (a.get('pub_date_iso') and datetime.fromisoformat(a['pub_date_iso']) > cutoff)
        or not a.get('pub_date_iso')
    ]
    print(f"After dropping articles older than {ROLLING_DAYS} days: {len(existing)} articles remain")

    print("\nFetching RSS feeds...")
    new_raw = fetch_articles()

    new_articles = [a for a in new_raw if a['url'] not in existing_urls]
    print(f"\nNew articles to process: {len(new_articles)}")

    if not new_articles:
        print("No new articles — archive is up to date")
    else:
        print("\nFetching meta descriptions...")
        for i, article in enumerate(new_articles):
            meta = fetch_meta_description(article['url'])
            article['meta_description'] = meta
            status = "✓" if meta else "✗"
            print(f"  {status} [{i+1}/{len(new_articles)}] {article['source']}: {article['title'][:45]}...")
            time.sleep(0.2)

        if not ANTHROPIC_API_KEY:
            print("\n⚠ No ANTHROPIC_API_KEY found — skipping AI analysis, using raw summaries")
        else:
            print("\nRunning AI analysis on new articles...")

        processed_new = []
        for i, article in enumerate(new_articles):
            print(f"  [{i+1}/{len(new_articles)}] {article['title'][:55]}...")
            analysis = analyse_article(article)
            if ANTHROPIC_API_KEY:
                time.sleep(0.3)

            processed_new.append({
                "title": article["title"],
                "url": article["url"],
                "source": article["source"],
                "date": article["date"],
                "pub_date_iso": article["pub_date_iso"],
                "summary": analysis["summary"],
                "tone": analysis["tone"],
                "topic": analysis["topic"],
                "low_confidence": analysis.get("low_confidence", False),
                "raw_rss": article.get("raw_rss", ""),
                "raw_content": article.get("raw_content", ""),
                "raw_meta": article.get("meta_description", ""),
            })

        existing = existing + processed_new

    existing.sort(key=lambda a: a.get('pub_date_iso', ''), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topics": TOPICS,
        "articles": existing,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Done! {len(existing)} articles in rolling archive")

if __name__ == "__main__":
    main()
