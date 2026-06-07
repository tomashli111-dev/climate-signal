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
    {"source": "GB News",          "url": "https://www.gbnews.com/feeds/news.rss",                            "max": 50},
    {"source": "GB News",          "url": "https://www.gbnews.com/feeds/politics.rss",                        "max": 30},
    {"source": "GB News",          "url": "https://www.gbnews.com/feeds/opinion.rss",                         "max": 30},
    {"source": "Daily Mail",       "url": "https://www.dailymail.co.uk/sciencetech/index.rss",                "max": 50},
    {"source": "Daily Mail",       "url": "https://www.dailymail.co.uk/news/environment/index.rss",           "max": 30},
    {"source": "The Sun",          "url": "https://www.thesun.co.uk/feed/",                                   "max": 50},
    {"source": "The Spectator",    "url": "https://www.spectator.co.uk/feed/",                                "max": 50},
    {"source": "The Express",      "url": "https://www.express.co.uk/posts/rss",                              "max": 50},

    # Centre
    {"source": "BBC Environment",  "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",    "max": 20},
    {"source": "Sky News",         "url": "https://feeds.skynews.com/feeds/rss/home.xml",                     "max": 50},
    {"source": "Sky News",         "url": "https://feeds.skynews.com/feeds/rss/politics.xml",                 "max": 30},
    {"source": "Evening Standard", "url": "https://www.standard.co.uk/news/rss",                              "max": 50},
    {"source": "The i",            "url": "https://inews.co.uk/feed",                                         "max": 20},

    # Centre-left
    {"source": "The Guardian",     "url": "https://www.theguardian.com/environment/climate-crisis/rss",       "max": 20},
    {"source": "The Guardian",     "url": "https://www.theguardian.com/environment/rss",                      "max": 20},
    {"source": "The Independent",  "url": "https://www.independent.co.uk/rss",                                "max": 50},
    {"source": "The Independent",  "url": "https://www.independent.co.uk/climate-change/rss",                 "max": 20},
    {"source": "The Mirror",       "url": "https://www.mirror.co.uk/?service=rss",                            "max": 50},
    {"source": "The Mirror",       "url": "https://www.mirror.co.uk/science/?service=rss",                    "max": 30},
    {"source": "Channel 4 News",   "url": "https://www.channel4.com/news/feed",                               "max": 50},
]

ROLLING_DAYS = 7
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
JINA_MIN_LENGTH = 200  # minimum characters to consider Jina result useful

# ─────────────────────────────────────────────
# KEYWORD FILTER
# ─────────────────────────────────────────────
TIER1 = [
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
    'paris agreement', 'cop29', 'cop30', 'cop31', 'ipcc', 'unfccc',
    'emissions trading', 'emissions target', 'emissions reduction',
    'just transition', 'green new deal', 'loss and damage fund',
    'nature-based solutions', 'biodiversity net gain', 'environment act',
    'seventh carbon budget', 'sixth carbon budget', 'clean power 2030',
    'great british energy', 'energy security bill', 'climate change committee',
    'net zero strategy', 'green finance',
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
    'electric vehicle', 'electric car', 'ev charging', 'ev mandate',
    'petrol ban', 'diesel ban', 'boiler ban', 'boiler upgrade', 'heat pump',
    'ulez', 'low emission zone', 'war on motorists', 'war on drivers',
    'ban on petrol', 'ban on diesel', 'zero emission vehicle',
    'biodiversity', 'species extinction', 'habitat loss', 'deforestation',
    'reforestation', 'rewilding', 'ocean acidification', 'sea level rise',
    'arctic ice', 'arctic melt', 'glacier retreat', 'permafrost',
    'coral reef', 'coral bleaching', 'marine protected area', 'nature recovery',
    'wildlife corridor', 'species decline', 'bee population', 'insect population',
    'endangered species', 'habitat destruction', 'rainforest destruction',
    'mangrove', 'kelp forest', 'peatland', 'wetlands loss',
    'plastic pollution', 'water pollution', 'toxic waste',
    'sewage dumping', 'river pollution', 'air pollution', 'particulate matter',
    'nitrogen dioxide', 'pm2.5', 'chemical pollution',
    'green blob', 'eco zealot', 'eco madness', 'green madness',
    'net zero madness', 'net zero cost', 'net zero burden', 'net zero bill',
    'green ideology', 'green obsession', 'green targets', 'eco activist',
    'extinction rebellion', 'just stop oil', 'insulate britain',
    'greenwashing', 'wind farm backlash', 'solar farm backlash',
    'hottest year', 'hottest ever', 'record temperature', 'record heat',
    'extreme weather event', 'ipcc report', 'global temperature',
    'temperature record', 'sea level', 'el nino', 'el niño',
    'sea defences', 'environment agency', 'natural england',
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
    'el nino', 'flood risk', 'microplastics',
]

def is_relevant(article):
    text = (
        article.get('title', '') + ' ' +
        article.get('raw_rss', '') + ' ' +
        article.get('raw_content', '') + ' ' +
        article.get('jina_text', '')
    ).lower()
    if any(kw in text for kw in TIER1):
        return True
    tier2_matches = sum(1 for kw in TIER2 if kw in text)
    if tier2_matches >= 2:
        return True
    return False

# ─────────────────────────────────────────────
# FETCH FULL ARTICLE TEXT VIA JINA
# ─────────────────────────────────────────────
def fetch_article_text(url):
    """
    Try Jina Reader first for full article text.
    Falls back to meta description if Jina fails or returns too little.
    Returns (jina_text, meta_description, source_used)
    """
    jina_text = ""
    meta_description = ""

    # Try Jina Reader
    try:
        jina_url = f"https://r.jina.ai/{url}"
        req = Request(jina_url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ClimateSignalBot/1.0)',
            'Accept': 'text/plain',
            'X-Return-Format': 'text',
        })
        with urlopen(req, timeout=15) as response:
            raw = response.read(100000).decode('utf-8', errors='ignore')
            # Strip Jina metadata header (first few lines)
            lines = raw.split('\n')
            content_lines = [l for l in lines if not l.startswith('Title:') and
                           not l.startswith('URL:') and
                           not l.startswith('Published') and
                           not l.startswith('Description:') and
                           not l.startswith('Warning:')]
            jina_text = '\n'.join(content_lines).strip()
            jina_text = jina_text[:3000]  # cap at 3000 chars for Claude

    except Exception:
        pass

    # Try meta description as fallback / supplement
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ClimateSignalBot/1.0)',
            'Accept': 'text/html',
        })
        with urlopen(req, timeout=10) as response:
            html = response.read(50000).decode('utf-8', errors='ignore')
        og = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if og:
            meta_description = og.group(1).strip()
        else:
            meta = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
            if meta:
                meta_description = meta.group(1).strip()
    except Exception:
        pass

    return jina_text, meta_description

def get_source_used(jina_text, meta_description, raw_rss, raw_content):
    """Calculate what data sources are actually available for analysis."""
    parts = []
    if len(jina_text) >= JINA_MIN_LENGTH:
        parts.append('full article (Jina)')
    if raw_content and len(raw_content) > len(raw_rss or ''):
        parts.append('full RSS content')
    if raw_rss and len(raw_rss.strip()) > 30:
        parts.append('RSS excerpt')
    if meta_description and len(meta_description.strip()) > 30 and meta_description.strip() != raw_rss:
        parts.append('page description')
    return ' + '.join(parts) if parts else 'title only'

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

            print(f"✓ {feed_config['source']}: {count} articles")
        except Exception as e:
            print(f"✗ {feed_config['source']}: {e}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            unique.append(a)

    # Keyword filter — uses RSS text at this stage
    filtered = []
    for article in unique:
        if is_relevant(article):
            filtered.append(article)
        else:
            print(f"  ✗ Filtered out: {article['title'][:60]}")

    print(f"After keyword filter: {len(filtered)}/{len(unique)} articles kept")
    return filtered

# ─────────────────────────────────────────────
# CLAUDE API HELPERS
# ─────────────────────────────────────────────
def claude(prompt, max_tokens=500):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        payload = json.dumps({
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "max_tokens": max_tokens,
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
            return text
    except Exception as e:
        print(f"  Claude API error: {e}")
        return None

# ─────────────────────────────────────────────
# STEP 1: GENERATE TOPICS FROM ALL ARTICLES
# ─────────────────────────────────────────────
def generate_topics(all_articles):
    if not ANTHROPIC_API_KEY:
        return ["General"]

    headlines = "\n".join([
        f"- [{a['source']}] {a['title']}"
        for a in all_articles
    ])

    prompt = f"""You are analysing a set of climate and environment news headlines from UK media outlets over the past 7 days.

Here are all the headlines:
{headlines}

Identify 5-8 distinct topics that best group these articles. Topics should be:
- Specific enough to be meaningful (e.g. "Seventh Carbon Budget" not just "Climate Policy")
- Broad enough that multiple articles fit
- Named as a news editor would label a story cluster
- Reflective of what's actually in the news this week
- Mutually exclusive — topics must not overlap. An article should clearly belong to one topic only
- If two potential topics are closely related, merge them into one broader topic rather than keeping them separate

Bad example: having both "Net Zero Policy" and "UK Climate Targets" as separate topics — these overlap
Good example: merging them into "UK Net Zero and Climate Targets"

Respond with ONLY a JSON array of topic name strings, e.g.:
["Seventh Carbon Budget", "North Sea Oil Licensing", "EV Mandate Debate", "Nature Recovery"]

No other text."""

    result = claude(prompt, max_tokens=300)
    if not result:
        return ["General"]
    try:
        topics = json.loads(result)
        if isinstance(topics, list) and len(topics) > 0:
            print(f"Generated {len(topics)} topics: {topics}")
            return topics
    except Exception as e:
        print(f"  Topic generation error: {e}")
    return ["General"]

# ─────────────────────────────────────────────
# STEP 2: ASSIGN ARTICLE TO TOPIC + SUMMARY
# ─────────────────────────────────────────────
def analyse_article(article, topics):
    # Build best available source data
    jina_text = article.get('jina_text', '')
    meta = article.get('raw_meta', '')
    raw_rss = article.get('raw_rss', '')
    raw_content = article.get('raw_content', '')
    source_used = article.get('source_used', 'RSS excerpt only')

    # Pick richest available text
    if len(jina_text) >= JINA_MIN_LENGTH:
        primary_text = jina_text[:2000]
    elif raw_content:
        primary_text = raw_content
    elif meta:
        primary_text = meta
    else:
        primary_text = raw_rss

    available_text = primary_text.strip()

    if not ANTHROPIC_API_KEY:
        return {
            "summary": article.get("raw_summary", "")[:200],
            "topic": topics[0] if topics else "General",
            "low_confidence": len(available_text) < 50,
        }

    low_confidence = len(available_text) < 50
    if low_confidence:
        return {
            "summary": "Insufficient source data — click to read the full article.",
            "topic": topics[0] if topics else "General",
            "low_confidence": True,
        }

    source_data = f"Title: {article['title']}\nSource: {article['source']}\n"
    source_data += f"Article text ({source_used}):\n{available_text}\n"

    # Add RSS excerpt too if it's different and we have full text
    if len(jina_text) >= JINA_MIN_LENGTH and raw_rss and raw_rss not in jina_text[:200]:
        source_data += f"RSS excerpt: {raw_rss[:200]}\n"

    topics_list = "\n".join(f"- {t}" for t in topics)

    prompt = f"""You are analysing a climate and environment news article for a media monitoring tool.

Available data:
{source_data}

Important: Base your summary ONLY on the information provided above. Do not add details not present in the source.

Topics available — each is mutually exclusive, pick the single best fit:
{topics_list}

If the article could fit multiple topics, choose the one that best matches the PRIMARY subject of the article.

Respond with ONLY a JSON object:
{{
  "summary": "2-3 sentence plain-English summary based strictly on the source data.",
  "topic": "exact topic name from the list above"
}}

No other text."""

    result = claude(prompt, max_tokens=300)
    if result:
        try:
            parsed = json.loads(result)
            return {
                "summary": parsed.get("summary", ""),
                "topic": parsed.get("topic", topics[0]),
                "low_confidence": False,
            }
        except Exception:
            pass

    return {
        "summary": available_text[:200],
        "topic": topics[0] if topics else "General",
        "low_confidence": True,
    }

# ─────────────────────────────────────────────
# STEP 3: GENERATE TOPIC META-SUMMARIES
# ─────────────────────────────────────────────
def generate_topic_summary(topic, articles):
    if not ANTHROPIC_API_KEY or len(articles) < 1:
        return ""

    headlines_by_source = "\n".join([
        f"- {a['source']}: {a['title']}"
        for a in articles
    ])

    prompt = f"""You are a media analyst summarising how UK news outlets are covering a climate/environment topic.

Topic: {topic}

Headlines from different outlets:
{headlines_by_source}

Write 2-4 sentences that:
1. Briefly describe what specific events or developments are being covered (not just the general topic) — mention specific events, figures, or developments referenced in the headlines
2. If there are multiple outlets, note how different outlets are framing or emphasising the story differently

Important: Base this ONLY on the headlines above. Do not add outside knowledge. Start directly with the content, no preamble.

Keep it under 80 words."""

    result = claude(prompt, max_tokens=150)
    return result or ""

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
    print(f"After pruning: {len(existing)} articles remain")

    print("\nFetching RSS feeds...")
    new_raw = fetch_articles()
    new_articles = [a for a in new_raw if a['url'] not in existing_urls]
    print(f"\nNew articles to process: {len(new_articles)}")

    # Fetch full article text via Jina + meta description
    if new_articles:
        print("\nFetching article text via Jina Reader...")
        for i, article in enumerate(new_articles):
            jina_text, meta_desc = fetch_article_text(article['url'])
            article['jina_text'] = jina_text
            article['raw_meta'] = meta_desc
            article['source_used'] = get_source_used(jina_text, meta_desc, article.get('raw_rss',''), article.get('raw_content',''))
            status = "✓ full" if len(jina_text) >= JINA_MIN_LENGTH else ("✓ meta" if meta_desc else "✗ rss only")
            print(f"  {status} [{i+1}/{len(new_articles)}] {article['source']}: {article['title'][:40]}...")
            time.sleep(3)  # stay within Jina's 20 RPM free tier limit

    # Build processed new articles
    processed_new = []
    for article in new_articles:
        processed_new.append({
            "title": article["title"],
            "url": article["url"],
            "source": article["source"],
            "date": article["date"],
            "pub_date_iso": article["pub_date_iso"],
            "raw_rss": article.get("raw_rss", ""),
            "raw_content": article.get("raw_content", ""),
            "raw_meta": article.get("raw_meta", ""),
            "jina_text": article.get("jina_text", ""),
            "source_used": article.get("source_used", "RSS excerpt only"),
            "raw_summary": article.get("raw_summary", ""),
            "summary": "",
            "topic": "",
            "low_confidence": False,
        })

    all_articles = existing + processed_new

    if not ANTHROPIC_API_KEY:
        print("\n⚠ No ANTHROPIC_API_KEY — skipping AI analysis")
        for a in all_articles:
            if not a.get('summary'):
                a['summary'] = a.get('raw_summary', '')[:200]
            if not a.get('topic'):
                a['topic'] = 'General'
        topic_summaries = {}
    else:
        print(f"\nGenerating topics for {len(all_articles)} articles...")
        topics = generate_topics(all_articles)
        time.sleep(0.5)

        print(f"\nAnalysing all {len(all_articles)} articles...")
        for i, article in enumerate(all_articles):
            print(f"  [{i+1}/{len(all_articles)}] {article['title'][:55]}...")
            analysis = analyse_article(article, topics)
            article['summary'] = analysis['summary']
            article['topic'] = analysis['topic']
            article['low_confidence'] = analysis.get('low_confidence', False)
            time.sleep(0.3)

        print("\nGenerating topic summaries...")
        topic_summaries = {}
        grouped = {}
        for a in all_articles:
            t = a.get('topic', 'General')
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(a)

        for topic, arts in grouped.items():
            if len(arts) >= 1:
                print(f"  Summarising: {topic} ({len(arts)} articles)...")
                summary = generate_topic_summary(topic, arts)
                topic_summaries[topic] = summary
                time.sleep(0.3)

    all_articles.sort(key=lambda a: a.get('pub_date_iso', ''), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topic_summaries": topic_summaries if ANTHROPIC_API_KEY else {},
        "articles": all_articles,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Done! {len(all_articles)} articles in rolling archive")

if __name__ == "__main__":
    main()
