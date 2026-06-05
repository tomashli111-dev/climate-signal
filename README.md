# Climate Signal

A personal climate news aggregator that pulls articles from major outlets daily and uses Claude AI to generate plain-English summaries and tone analysis — tracking not just *what* is reported, but *how*.

## What it does

- Fetches the latest climate articles from 6+ RSS feeds every morning at 7am UTC
- Uses the Anthropic API (Claude) to summarise each article and classify its tone
- Publishes a clean, filterable website via GitHub Pages — no server needed

## Tone categories

| Tone | Meaning |
|------|---------|
| Alarmist | Urgent crisis framing, fear-led language |
| Hopeful | Progress, optimism, positive outcomes |
| Neutral | Factual, measured, reportorial |
| Solutions | Centres on fixes — tech, policy, behaviour |
| Political | Policy debate, blame, partisan framing |

## Setup

### 1. Add your Anthropic API key

Go to **Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Value: your key from console.anthropic.com

### 2. Enable GitHub Pages

Go to **Settings → Pages**

- Source: **Deploy from a branch**
- Branch: `main`, folder: `/docs`

### 3. Run the first build

Go to **Actions → Daily article build → Run workflow**

Your site will be live at `https://YOUR-USERNAME.github.io/climate-signal`

## Adding more sources

Edit the `RSS_FEEDS` list in `build.py` — add any RSS feed URL and a source name.

## Cost

- GitHub: free
- Anthropic API: ~£1–3/month at 30 articles/day
- Custom domain (optional): ~£10/year
