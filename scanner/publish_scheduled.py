"""Publishes scheduled articles whose release time has arrived.
Runs in GitHub Actions during scheduled scans (even if the user's laptop is offline)
and can also be invoked locally by the FastAPI server or manually.
"""
import json, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEDULED_FILE = ROOT / "data" / "scheduled_articles.json"
DOCS_ARTICLES = ROOT / "docs" / "articles.json"
LOCAL_ARTICLES = ROOT / "local" / "articles.json"

def to_ms(val):
    if not val:
        return 0
    if isinstance(val, (int, float)):
        # If in seconds (< 10^11), convert to ms
        return int(val * 1000) if val < 100000000000 else int(val)
    if isinstance(val, str):
        try:
            # ISO format: 2026-11-07T12:00 or 2026-11-07T12:00:00Z
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            try:
                f = float(val)
                return int(f * 1000) if f < 100000000000 else int(f)
            except Exception:
                return 0
    return 0

def check_and_publish():
    if not SCHEDULED_FILE.exists():
        return 0, []
    
    try:
        scheduled = json.loads(SCHEDULED_FILE.read_text("utf-8"))
    except Exception as e:
        print(f"Error reading scheduled_articles.json: {e}")
        return 0, []
    
    if not scheduled:
        return 0, []

    now_ms = int(time.time() * 1000)
    due_items = []
    remaining = []

    for item in scheduled:
        sched_time = to_ms(item.get("scheduled_for"))
        if sched_time > 0 and sched_time <= now_ms:
            due_items.append(item)
        else:
            remaining.append(item)

    if not due_items:
        return 0, []

    # Load public docs/articles.json
    try:
        articles = json.loads(DOCS_ARTICLES.read_text("utf-8")) if DOCS_ARTICLES.exists() else []
    except Exception:
        articles = []

    # Load local articles if exists
    local_db = {}
    if LOCAL_ARTICLES.exists():
        try:
            local_db = json.loads(LOCAL_ARTICLES.read_text("utf-8"))
        except Exception:
            local_db = {}

    published_titles = []
    for art in due_items:
        art["status"] = "published"
        art["published_at"] = now_ms
        aid = art.get("id")

        # Deduplicate in public articles
        articles = [x for x in articles if x.get("id") != aid]
        articles.insert(0, art)

        # Update local db if present
        if aid in local_db:
            local_db[aid]["status"] = "published"
            local_db[aid]["published_at"] = now_ms

        published_titles.append(art.get("title", aid))

    # Save docs/articles.json
    DOCS_ARTICLES.parent.mkdir(parents=True, exist_ok=True)
    DOCS_ARTICLES.write_text(json.dumps(articles, ensure_ascii=False, indent=2), "utf-8")

    # Rebuild RSS & Atom feeds for Substack and aggregators
    try:
        try:
            from . import generate_feed
        except ImportError:
            import generate_feed
        generate_feed.build_all()
    except Exception as e:
        print(f"Feed rebuild notice: {e}")

    # Save remaining scheduled
    SCHEDULED_FILE.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), "utf-8")

    # Save local db
    if local_db and LOCAL_ARTICLES.exists():
        LOCAL_ARTICLES.write_text(json.dumps(local_db, ensure_ascii=False, indent=2), "utf-8")

    print(f"Published {len(due_items)} scheduled article(s): {', '.join(published_titles)}")
    return len(due_items), published_titles

if __name__ == "__main__":
    count, titles = check_and_publish()
    if count == 0:
        print("No scheduled articles due for publishing.")
