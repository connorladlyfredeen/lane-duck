"""Prerender a static, crawlable HTML page of every pool and its lane swim
times from the scraped cache.

The main app (index.html) renders the pool list client-side with Vue, so search
engines see almost no content. This script reads tmp/good_list_cache.json and
writes a fully static page (pool_schedules.html) listing each pool's name,
address, indoor/outdoor, official link, and upcoming lane swim times — so the
actual pool names and schedules are crawlable. It is regenerated on every scrape
run (see scrape.py) so it stays fresh, and is served at /lane-duck/pools.
"""
import json
import os
import re
import html
from datetime import datetime
from collections import defaultdict

CACHE_FILE = "tmp/good_list_cache.json"
OUTPUT_FILE = "pool_schedules.html"
SITE_URL = "https://www.connorladly.com/lane-duck"


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fmt_time(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S").strftime("%-I:%M %p")


def fmt_day(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S").strftime("%A, %B %-d")


def stamp_sitemap(sitemap_file="sitemap.xml"):
    """Update every <lastmod> in sitemap.xml to today's date (America/Toronto).

    The sitemap advertises changefreq=daily, so a stale lastmod is a weak SEO
    signal. This is called on every scrape run so the served sitemap always
    reflects the day the data was last refreshed. No-op (with a warning) if the
    sitemap is missing, so it can never break the scrape."""
    if not os.path.exists(sitemap_file):
        print(f"stamp_sitemap: {sitemap_file} not found, skipping")
        return None
    from scrape import now_toronto
    today = now_toronto().strftime("%Y-%m-%d")
    with open(sitemap_file, "r", encoding="utf-8") as f:
        xml = f.read()
    new_xml, n = re.subn(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{today}</lastmod>", xml)
    if new_xml != xml:
        with open(sitemap_file, "w", encoding="utf-8") as f:
            f.write(new_xml)
    print(f"stamp_sitemap: set {n} <lastmod> entries to {today}")
    return today


def build_beaches(cache_file="tmp/beaches_cache.json", html_file="beaches.html"):
    """Inject a static, crawlable snapshot of current beach conditions into
    beaches.html (between the BEACHES_STATIC markers). Gives search engines real
    content and doubles as the fallback shown if the interactive app can't load.
    Fully non-fatal: missing cache/markers/file just skips."""
    START, END = "<!-- BEACHES_STATIC_START -->", "<!-- BEACHES_STATIC_END -->"
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            beaches = json.load(f)
        with open(html_file, "r", encoding="utf-8") as f:
            page = f.read()
    except (FileNotFoundError, ValueError) as e:
        print(f"build_beaches: skipped ({e})")
        return None
    if START not in page or END not in page or not beaches:
        print("build_beaches: markers missing or no beaches, skipped")
        return None

    def status_span(s):
        cls = {"SAFE": "bs-safe", "UNSAFE": "bs-unsafe"}.get(s, "bs-unknown")
        label = {"SAFE": "🟢 Safe to swim", "UNSAFE": "🔴 Unsafe"}.get(s, "⚪ No recent data")
        return f'<span class="{cls}">{label}</span>'

    def fmt_date(iso):
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%B %-d")
        except (ValueError, TypeError):
            return iso or "n/a"

    dates = [b.get("sample_date") for b in beaches if b.get("sample_date")]
    latest = fmt_date(max(dates)) if dates else "the latest sampling day"
    safe = sum(1 for b in beaches if b.get("status") == "SAFE")
    unsafe = sum(1 for b in beaches if b.get("status") == "UNSAFE")

    items = []
    for b in sorted(beaches, key=lambda x: x.get("beach_name", "")):
        name = html.escape(b.get("beach_name", "").strip())
        eco = b.get("ecoli")
        bits = []
        if eco is not None:
            bits.append(f"E. coli {html.escape(str(eco))}")
        if b.get("sample_date"):
            bits.append(f"sampled {fmt_date(b['sample_date'])}")
        if b.get("blue_flag"):
            bits.append("Blue Flag")
        detail = f" ({', '.join(bits)})" if bits else ""
        items.append(f"      <li>{status_span(b.get('status'))} — <strong>{name}</strong>{detail}</li>")

    snapshot = (
        f"\n        <p>As of {latest}, {len(beaches)} Toronto supervised beaches are monitored for water quality — "
        f"{safe} currently safe to swim{f', {unsafe} posted unsafe' if unsafe else ''}. "
        f"Toronto Public Health samples E. coli daily in summer; a beach is posted unsafe above 100 E. coli/100 mL.</p>\n"
        f"    <ul>\n{os.linesep.join(items)}\n    </ul>\n    "
    )

    new_page = page[:page.index(START) + len(START)] + snapshot + page[page.index(END):]
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(new_page)
    print(f"build_beaches: wrote snapshot for {len(beaches)} beaches ({safe} safe, {unsafe} unsafe)")
    return html_file


def build(cache_file=CACHE_FILE, output_file=OUTPUT_FILE):
    with open(cache_file, "r", encoding="utf-8") as f:
        pools = json.load(f)

    # Toronto wall-clock time (naive) so "already finished" is judged in the
    # pools' local timezone, matching the naive datetimes stored in the cache.
    # Uses the same fail-loud Toronto clock as the scraper (no silent UTC).
    from scrape import now_toronto
    now = now_toronto().replace(tzinfo=None)
    pools = sorted(pools, key=lambda p: p.get("complexname", ""))

    pool_sections = []
    total_sessions = 0
    for pool in pools:
        name = pool.get("complexname", "").strip()
        if not name:
            continue
        address = pool.get("address", "").strip()
        pool_type = pool.get("pool_type", "Indoor")
        website = pool.get("website", "")

        # Group upcoming sessions by day
        by_day = defaultdict(list)
        for s in pool.get("swim_data", []):
            try:
                end = datetime.strptime(s["end_time"], "%Y-%m-%dT%H:%M:%S")
            except (KeyError, ValueError, TypeError):
                continue
            if end < now:
                continue  # skip sessions already finished
            by_day[s["start_time"][:10]].append(s)

        if not by_day:
            continue

        day_html = []
        for day_key in sorted(by_day):
            sessions = sorted(by_day[day_key], key=lambda s: s["start_time"])
            times = ", ".join(
                f"{fmt_time(s['start_time'])}&ndash;{fmt_time(s['end_time'])}" for s in sessions
            )
            total_sessions += len(sessions)
            day_html.append(
                f'      <li><span class="day">{html.escape(fmt_day(sessions[0]["start_time"]))}:</span> {times}</li>'
            )

        name_html = html.escape(name)
        title_html = (
            f'<a href="{html.escape(website)}" target="_blank" rel="noopener">{name_html}</a>'
            if website
            else name_html
        )
        meta_bits = []
        if address:
            meta_bits.append(html.escape(address))
        pool_length = pool.get("pool_length", "Unknown")
        type_bit = f"{html.escape(pool_type)} pool"
        if pool_length and pool_length != "Unknown":
            type_bit += f" &middot; {html.escape(pool_length)}"
        meta_bits.append(type_bit)
        pool_sections.append(
            f'''  <section class="pool" id="{slugify(name)}">
    <h2>{title_html}</h2>
    <p class="meta">{' &middot; '.join(meta_bits)}</p>
    <ul class="times">
{os.linesep.join(day_html)}
    </ul>
  </section>'''
        )

    # ItemList structured data of the pools (crawlable list of names + anchors)
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Toronto public pools with lane swimming",
        "numberOfItems": len(pool_sections),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": p.get("complexname", "").strip(),
                "url": f"{SITE_URL}/pools#{slugify(p.get('complexname', '').strip())}",
            }
            for i, p in enumerate(
                [p for p in pools if p.get("complexname", "").strip()]
            )
        ],
    }

    updated = now.strftime("%B %-d, %Y at %-I:%M %p")
    page = f'''<!DOCTYPE html>
<html lang="en-CA">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>All Toronto Pool Lane Swim Schedules &amp; Times | LaneDuck 🦆</title>
<meta name="description" content="Full lane swim (lap swim) schedule for every Toronto public pool with lane swimming — indoor and outdoor, with times, addresses, and directions. Updated daily.">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{SITE_URL}/pools">
<meta property="og:title" content="All Toronto Pool Lane Swim Schedules | LaneDuck">
<meta property="og:description" content="Lane swim times for every Toronto public pool with lane swimming, indoor and outdoor. Updated daily.">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}/pools">
<meta property="og:image" content="{SITE_URL}/og-image.png">
<meta name="geo.region" content="CA-ON">
<meta name="geo.placename" content="Toronto">
<script type="application/ld+json">
{json.dumps(item_list, ensure_ascii=False, indent=2)}
</script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; color:#1C2B2A; background:#f4f7f7; line-height:1.55; padding:24px 16px 64px; }}
  .wrap {{ max-width:820px; margin:0 auto; }}
  header {{ background:linear-gradient(135deg,#1AA8A0 0%,#14837d 100%); color:#fff; border-radius:14px; padding:32px 28px; margin-bottom:24px; }}
  header h1 {{ font-size:1.9rem; margin-bottom:8px; }}
  header p {{ opacity:.95; }}
  header a {{ color:#fff; font-weight:600; }}
  .intro {{ background:#fff; border:1px solid #e2e8e8; border-radius:12px; padding:18px 20px; margin-bottom:24px; font-size:.96rem; }}
  .intro a {{ color:#12766f; font-weight:600; }}
  .pool {{ background:#fff; border:1px solid #e2e8e8; border-radius:12px; padding:18px 20px; margin-bottom:14px; }}
  .pool h2 {{ font-size:1.18rem; margin-bottom:2px; }}
  .pool h2 a {{ color:#12766f; text-decoration:none; }}
  .pool h2 a:hover {{ text-decoration:underline; }}
  .meta {{ color:#5b6b6a; font-size:.85rem; margin-bottom:10px; }}
  .times {{ list-style:none; display:flex; flex-direction:column; gap:4px; }}
  .times li {{ font-size:.9rem; }}
  .day {{ font-weight:600; color:#12766f; }}
  footer {{ margin-top:28px; color:#5b6b6a; font-size:.85rem; text-align:center; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background:#0f1514; color:#e8efee; }}
    .intro,.pool {{ background:#151d1c; border-color:#25322f; }}
    .pool h2 a,.day {{ color:#2fc3ba; }}
    .meta,footer {{ color:#9fb0ae; }}
    .intro a {{ color:#2fc3ba; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>All Toronto Pool Lane Swim Schedules</h1>
    <p>Lane swim times for every Toronto public pool with lane swimming — indoor &amp; outdoor. <a href="{SITE_URL}">← Back to the LaneDuck finder</a></p>
  </header>
  <div class="intro">
    <p>This page lists <strong>{len(pool_sections)} Toronto public pools</strong> with upcoming lane swim (lap swim) sessions — {total_sessions} sessions in total, updated daily. Tap a pool name for its official City of Toronto page. For an interactive version where you can filter by date, indoor/outdoor, and sort by distance, use the <a href="{SITE_URL}">LaneDuck lane swim finder</a>.</p>
  </div>
{os.linesep.join(pool_sections)}
  <footer>Schedule data from the City of Toronto, updated {updated}. Always confirm times on the pool's official page before visiting.</footer>
</div>
</body>
</html>
'''

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Prerendered {len(pool_sections)} pools ({total_sessions} sessions) -> {output_file}")
    return output_file


if __name__ == "__main__":
    build()
