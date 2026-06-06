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
    # Right-leaning / sceptic — high volume, need more articles
    {"source": "The Spectator",        "url": "https://www.spectator.co.uk/feed/",                                 "max": 50},
    {"source": "GB News",              "url": "https://www.gbnews.com/feeds/news.rss",                             "max": 50},
    {"source": "Daily Mail",           "url": "https://www.dailymail.co.uk/news/environment/index.rss",            "max": 50},

    # Centre
    {"source": "BBC Environment",      "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",     "max": 20},
    {"source": "Reuters",              "url": "https://feeds.reuters.com/reuters/environment",                      "max": 20},
    {"source": "Sky News",             "url": "https://feeds.skynews.com/feeds/rss/environment.xml",               "max": 20},

    # Centre-left
    {"source": "The Guardian",         "url": "https://www.theguardian.com/environment/climate-crisis/rss",        "max": 20},
    {"source": "The Independent",      "url": "https://www.independent.co.uk/climate-change/rss",                  "max": 20},

    # Specialist
    {"source": "Carbon Brief",         "url": "https://www.carbonbrief.org/feed/",                                 "max": 10},
    {"source": "Climate Home News",    "url": "https://www.climatechangenews.com/feed/",                           "max": 10},

    # Science
    {"source": "Yale Environment 360", "url": "https://e360.yale.edu/feed.xml",                                    "max": 10},
    {"source": "NASA Climate",         "url": "https://climate.nasa.gov/news/rss.xml",                             "max": 10},
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
    'global warming', 'greenhouse gas', 'greenhouse effect',
    'carbon emissions', 'carbon footprint', 'carbon capture', 'carbon offset',
    'carbon tax', 'carbon budget', 'carbon neutral', 'carbon dioxide',
    'carbon price', 'carbon market', 'carbon border', 'carbon tariff',
    'stranded assets', 'scope 3 emissions', 'methane emissions',
    'net zero', 'decarbonisation', 'decarbonization',

    # Policy & agreements
    'paris agreement', 'cop29', 'cop30', 'ipcc', 'unfccc',
    'emissions trading', 'emissions target', 'emissions reduction',
    'just transition', 'green new deal', 'loss and damage fund',
    'nature-based solutions', 'biodiversity net gain', 'environment act',
    'seventh carbon budget', 'sixth carbon budget', 'clean power 2030',
    'great british energy', 'energy security bill', 'climate change committee',

    # Energy — specific enough
    'fossil fuel', 'renewable energy', 'clean energy', 'energy transition',
    'offshore wind', 'wind farm', 'wind turbine', 'solar power', 'solar panel',
    'solar farm', 'green hydrogen', 'hydrogen fuel', 'tidal power', 'tidal energy',
    'nuclear energy', 'battery storage', 'energy storage', 'grid capacity',
    'north sea oil', 'north sea licence', 'rosebank oilfield',
    'cambo oilfield', 'fracking', 'coal power', 'coal mine',
    'oil industry', 'oil drilling', 'gas drilling', 'gas pipeline',

    # Transport & net zero policy
    'electric vehicle', 'ev charging', 'ev mandate', 'petrol ban',
    'diesel ban', 'boiler ban', 'boiler upgrade', 'heat pump',
    'ulez', 'low emission zone', 'war on motorists', 'war on drivers',
    'ban on petrol', 'ban on diesel',

    # Nature & biodiversity
    'biodiversity', 'species extinction', 'habitat loss', 'deforestation',
    'reforestation', 'rewilding', 'ocean acidification', 'sea level rise',
    'arctic ice', 'glacier retreat', 'permafrost', 'coral reef',
    'marine protected area', 'nature recovery', 'wildlife corridor',
    'species decline', 'bee population', 'insect population',

    # Pollution — specific
    'plastic pollution', 'microplastics', 'water pollution', 'toxic waste',
    'sewage dumping', 'river pollution', 'air pollution', 'particulate matter',
    'nitrogen dioxide', 'pm2.5',

    # Sceptic / tabloid framing
    'green blob', 'eco zealot', 'eco madness', 'green madness',
    'net zero madness', 'net zero cost', 'net zero burden', 'net zero bill',
    'green levies', 'green tax', 'green ideology',
    'green obsession', 'green targets', 'eco activist',
    'extinction rebellion', 'just stop oil', 'insulate britain',
    'greenwashing', 'fuel poverty', 'energy poverty',
    'wind subsidy', 'solar subsidy', 'wind farm backlash',

    # Science & reporting
    'hottest year', 'hottest ever', 'record temperature', 'record heat',
    'extreme weather event', 'climate report', 'ipcc report',
    'global temperature', 'temperature record',

    # UK specific policy
    'energy security bill', 'great british energy', 'national grid upgrade',
    'climate change committee', 'carbon budget uk',
    'north sea energy', 'clean power target',
]

TIER2 = [
    'flooding', 'flash flood', 'drought', 'heatwave', 'heat stress',
    'wildfire', 'water scarcity', 'storm surge', 'extreme weather',
    'energy bills', 'energy costs', 'energy crisis', 'energy price',
    'electricity price', 'heating costs',
    'sustainability', 'sustainable development',
    'circular economy', 'sustainable agriculture',
    'regenerative farming', 'soil health',
    'rainforest', 'wetlands', 'ecosystem', 'nature reserve',
    'coal industry', 'oil spill', 'gas leak', 'air quality',
]

def is_relevant(article):
    text = (article['title'] + ' ' + article['raw_summary']).lower()
    if any(kw in text for kw in TIER1):
        return True
    tier2_matches = sum(1 for kw in TIER2 if kw in text)
    if tier2_matches >= 2:
        return True
    return False

# ─────────────────────────────────────────────
# FETCH META DESCRIPTION FROM ARTICLE PAGE
# ─────────────────────────────────────────────
def fetch_meta_description(url):
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ClimateSignalBot/1.0)',
            'Accept': 'text/html',
        })
        with urlopen(req, timeout=10) as response:
            html = response.read(50000).decode('utf-8', errors='ignore')

        # Try og:description first (usually richer)
        og = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if og:
            return og.group(1).strip()

        # Fall back to standard meta description
        meta = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if meta:
            return meta.group(1).strip()

        return ""
    except Exception as e:
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
               TIER1 = [
    # Core climate
    'climate change', 'climate crisis', 'climate emergency', 'climate action',
    'climate policy', 'climate summit', 'climate target', 'climate model',
    'climate finance', 'climate activist', 'climate sceptic', 'climate skeptic',
    'climate denier', 'climate alarmist', 'climate hysteria', 'climate cult',
    'climate agenda', 'climate lobby', 'climate litigation', 'climate lawsuit',
    'global warming', 'greenhouse gas', 'greenhouse effect',
    'carbon emissions', 'carbon footprint', 'carbon capture', 'carbon offset',
    'carbon tax', 'carbon budget', 'carbon neutral', 'carbon dioxide',
    'carbon price', 'carbon market', 'carbon border', 'carbon tariff',
    'stranded assets', 'scope 3 emissions', 'methane emissions',
    'net zero', 'decarbonisation', 'decarbonization',

    # Policy & agreements
    'paris agreement', 'cop29', 'cop30', 'ipcc', 'unfccc',
    'emissions trading', 'emissions target', 'emissions reduction',
    'just transition', 'green new deal', 'loss and damage fund',
    'nature-based solutions', 'biodiversity net gain', 'environment act',
    'seventh carbon budget', 'sixth carbon budget', 'clean power 2030',
    'great british energy', 'energy security bill', 'climate change committee',

    # Energy — specific enough
    'fossil fuel', 'renewable energy', 'clean energy', 'energy transition',
    'offshore wind', 'wind farm', 'wind turbine', 'solar power', 'solar panel',
    'solar farm', 'green hydrogen', 'hydrogen fuel', 'tidal power', 'tidal energy',
    'nuclear energy', 'battery storage', 'energy storage', 'grid capacity',
    'north sea oil', 'north sea licence', 'rosebank oilfield',
    'cambo oilfield', 'fracking', 'coal power', 'coal mine',
    'oil industry', 'oil drilling', 'gas drilling', 'gas pipeline',

    # Transport & net zero policy
    'electric vehicle', 'ev charging', 'ev mandate', 'petrol ban',
    'diesel ban', 'boiler ban', 'boiler upgrade', 'heat pump',
    'ulez', 'low emission zone', 'war on motorists', 'war on drivers',
    'ban on petrol', 'ban on diesel',

    # Nature & biodiversity
    'biodiversity', 'species extinction', 'habitat loss', 'deforestation',
    'reforestation', 'rewilding', 'ocean acidification', 'sea level rise',
    'arctic ice', 'glacier retreat', 'permafrost', 'coral reef',
    'marine protected area', 'nature recovery', 'wildlife corridor',
    'species decline', 'bee population', 'insect population',

    # Pollution — specific
    'plastic pollution', 'microplastics', 'water pollution', 'toxic waste',
    'sewage dumping', 'river pollution', 'air pollution', 'particulate matter',
    'nitrogen dioxide', 'pm2.5',

    # Sceptic / tabloid framing
    'green blob', 'eco zealot', 'eco madness', 'green madness',
    'net zero madness', 'net zero cost', 'net zero burden', 'net zero bill',
    'green levies', 'green tax', 'green ideology',
    'green obsession', 'green targets', 'eco activist',
    'extinction rebellion', 'just stop oil', 'insulate britain',
    'greenwashing', 'fuel poverty', 'energy poverty',
    'wind subsidy', 'solar subsidy', 'wind farm backlash',

    # Science & reporting
    'hottest year', 'hottest ever', 'record temperature', 'record heat',
    'extreme weather event', 'climate report', 'ipcc report',
    'global temperature', 'temperature record',

    # UK specific policy
    'energy security bill', 'great british energy', 'national grid upgrade',
    'climate change committee', 'carbon budget uk',
    'north sea energy', 'clean power target',
]

TIER2 = [
    'flooding', 'flash flood', 'drought', 'heatwave', 'heat stress',
    'wildfire', 'water scarcity', 'storm surge', 'extreme weather',
    'energy bills', 'energy costs', 'energy crisis', 'energy price',
    'electricity price', 'heating costs',
    'sustainability', 'sustainable development',
    'circular economy', 'sustainable agriculture',
    'regenerative farming', 'soil health',
    'rainforest', 'wetlands', 'ecosystem', 'nature reserve',
    'coal industry', 'oil spill', 'gas leak', 'air quality',
]

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
                        "raw_summary": summary,
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
# CALL CLAUDE API FOR SUMMARY + TONE + TOPIC
# ─────────────────────────────────────────────
def analyse_article(article):
    if not ANTHROPIC_API_KEY:
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral",
            "topic": "Other",
        }

    # Build source data string from all available data
    source_data = f"Title: {article['title']}\n"
    source_data += f"Source: {article['source']}\n"
    if article.get('raw_summary'):
        source_data += f"RSS excerpt: {article['raw_summary']}\n"
    if article.get('meta_description') and article['meta_description'] != article['raw_summary']:
        source_data += f"Page description: {article['meta_description']}\n"

    topics_list = "\n".join(f"- {t}" for t in TOPICS)

    prompt = f"""You are analysing a climate and environment news article for a media monitoring tool.

Here is all the available data about this article:
{source_data}

Important: Base your analysis ONLY on the information provided above. Do not add details, statistics, or context that are not present in the source data. If the source data is limited, keep the summary brief and factual.

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
            }
    except Exception as e:
        print(f"  API error for '{article['title'][:40]}...': {e}")
        return {
            "summary": article["raw_summary"][:200] + "..." if len(article["raw_summary"]) > 200 else article["raw_summary"],
            "tone": "neutral",
            "topic": "Other",
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
        if a.get('pub_date_iso') and datetime.fromisoformat(a['pub_date_iso']) > cutoff
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
        # Fetch meta descriptions
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
                # Raw source data stored for transparency
                "raw_rss": article["raw_summary"],
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
