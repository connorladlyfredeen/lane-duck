"""Fetch Toronto beach water-quality advisories and write a cache the API serves.

Toronto Public Health samples its supervised beaches daily in summer and posts a
SAFE / UNSAFE swim advisory per beach. The City's own beach page is powered by two
JSON endpoints (below); we read the same feed, reduce it to the latest posting per
beach, and write tmp/beaches_cache.json for the /beaches API + the beaches page.

Degrades cleanly: any network/parse failure leaves the previous cache untouched and
never raises to the caller (the scrape must not fail because beaches are down).
Off-season the feed returns the last season's postings, so each beach carries its
`sample_date` and a `stale` flag and the UI says "as of <date>" instead of implying
it is today's reading.
"""
import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BEACH_LIST_URL = "https://secure.toronto.ca/opendata/adv/beach_list/v1?format=json"
BEACH_RESULTS_URL = "https://secure.toronto.ca/opendata/adv/beach_results/v1?format=json&startDate={start}&endDate={end}"
OUTPUT_FILE = "tmp/beaches_cache.json"
RESULTS_WINDOW_DAYS = 30   # look back far enough to find the latest posting, in or off season
STALE_AFTER_DAYS = 3       # older than this -> flag as possibly out of date


def _get_json(url):
    """GET a URL and parse JSON, reusing the scraper's retry/backoff helper."""
    from scrape import fetch_with_retries
    resp = fetch_with_retries(url)
    return resp.json()


def _latest_status_by_beach(results):
    """results: list of {CollectionDate, data:[{beachId, eColi, advisory, statusFlag}]}.
    Return {beachId: {status, ecoli, advisory, sample_date}} keeping, per beach, the
    most recent date that carries a posted status."""
    latest = {}
    for day in results or []:
        date = day.get("CollectionDate")
        if not date:
            continue
        for rec in day.get("data", []):
            bid = rec.get("beachId")
            if bid is None:
                continue
            flag = (rec.get("statusFlag") or "").upper()
            prev = latest.get(bid)
            # Prefer the newest date; among equal dates prefer one that has a status.
            if prev is None or date > prev["sample_date"] or (
                date == prev["sample_date"] and flag and not prev["status"]
            ):
                latest[bid] = {
                    "status": flag,                 # "SAFE" / "UNSAFE" / ""
                    "ecoli": rec.get("eColi"),
                    "advisory": rec.get("advisory") or "",
                    "sample_date": date,
                }
    return latest


def build(output_file=OUTPUT_FILE):
    from scrape import now_toronto
    today = now_toronto().date()

    try:
        beaches = _get_json(BEACH_LIST_URL)
        start = (today - timedelta(days=RESULTS_WINDOW_DAYS)).isoformat()
        results = _get_json(BEACH_RESULTS_URL.format(start=start, end=today.isoformat()))
    except Exception as e:
        logger.error(f"Beaches fetch failed (non-fatal); cache left as-is: {e}")
        return None

    status_by_beach = _latest_status_by_beach(results)

    out = []
    for b in beaches or []:
        bid = b.get("beachId")
        st = status_by_beach.get(bid, {})
        sample_date = st.get("sample_date")
        stale = True
        if sample_date:
            try:
                stale = (today - datetime.strptime(sample_date, "%Y-%m-%d").date()).days > STALE_AFTER_DAYS
            except ValueError:
                stale = True
        out.append({
            "beach_id": bid,
            "beach_name": (b.get("beachName") or "").strip(),
            "address": (b.get("address") or "").strip(),
            "blue_flag": (b.get("blueFlag") or "").upper() == "Y",
            "lat": b.get("lat"),
            "lon": b.get("lon"),
            "status": st.get("status") or "UNKNOWN",   # SAFE / UNSAFE / UNKNOWN
            "ecoli": st.get("ecoli"),
            "advisory": st.get("advisory") or "",
            "sample_date": sample_date,
            "stale": stale,
        })

    out.sort(key=lambda x: x["beach_name"])
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    safe = sum(1 for b in out if b["status"] == "SAFE")
    unsafe = sum(1 for b in out if b["status"] == "UNSAFE")
    logger.info(f"Beaches: wrote {len(out)} ({safe} safe, {unsafe} unsafe) -> {output_file}")
    print(f"Beaches: wrote {len(out)} beaches ({safe} safe, {unsafe} unsafe) -> {output_file}")
    return output_file


if __name__ == "__main__":
    build()
