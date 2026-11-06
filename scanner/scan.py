"""Collects trending projects, writes data/feed.json, autoposts to the Telegram channel.
Runs in GitHub Actions every 6 hours, and the laptop app reuses collect() for instant scans."""
import os, sys, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
FEED, STATE = ROOT / "data" / "feed.json", ROOT / "data" / "state.json"
UA = {"User-Agent": "pulsebyte"}

def iso(d): return (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
def jload(p, default):
    try: return json.loads(p.read_text("utf-8"))
    except Exception: return default
def get(url, params=None, headers=None):
    try:
        r = requests.get(url, params=params, headers={**UA, **(headers or {})}, timeout=25)
        return r.json() if r.ok else None
    except Exception: return None

def producthunt(token):
    if not token: return []
    try:
        r = requests.post("https://api.producthunt.com/v2/api/graphql", headers={**UA, "Authorization": "Bearer " + token}, timeout=25,
            json={"query": "{posts(order:RANKING,first:8){edges{node{id name tagline url votesCount createdAt}}}}"})
        return [x["node"] for x in r.json()["data"]["posts"]["edges"]]
    except Exception: return []

def collect():
    tok = os.getenv("GITHUB_TOKEN"); gh = {"Authorization": "Bearer " + tok} if tok else {}
    a = get("https://api.github.com/search/repositories", {"q": f"created:>{iso(7)}", "sort": "stars", "order": "desc", "per_page": 10}, gh) or {}
    b = get("https://gitlab.com/api/v4/projects", {"order_by": "star_count", "sort": "desc", "created_after": iso(30) + "T00:00:00Z", "per_page": 8}) or []
    c = get("https://codeberg.org/api/v1/repos/search", {"sort": "stars", "order": "desc", "limit": 50}) or {}
    d = get("https://huggingface.co/api/models", {"sort": "trendingScore", "limit": 8}) or get("https://huggingface.co/api/models", {"sort": "likes7d", "limit": 8}) or []
    items = []
    for r in a.get("items", []):
        items.append(dict(id=f"gh:{r['id']}", src="GitHub", name=r["full_name"], desc=r.get("description") or "", url=r["html_url"], score=r["stargazers_count"], lang=r.get("language") or "", topics=(r.get("topics") or [])[:5], created=r.get("created_at")))
    for r in (b if isinstance(b, list) else []):
        if (r.get("created_at") or "") > iso(30):
            items.append(dict(id=f"gl:{r['id']}", src="GitLab", name=r["path_with_namespace"], desc=r.get("description") or "", url=r["web_url"], score=r.get("star_count", 0), lang="", topics=(r.get("topics") or [])[:5], created=r.get("created_at")))
    for r in [x for x in (c.get("data") or []) if (x.get("created_at") or "") > iso(60)][:8]:
        items.append(dict(id=f"cb:{r['id']}", src="Codeberg", name=r["full_name"], desc=r.get("description") or "", url=r["html_url"], score=r.get("stars_count", 0), lang=r.get("language") or "", topics=[], created=r.get("created_at")))
    for r in (d if isinstance(d, list) else []):
        items.append(dict(id=f"hf:{r['id']}", src="HuggingFace", name=r["id"], desc=r.get("pipeline_tag") or "model", url="https://huggingface.co/" + r["id"], score=r.get("likes", 0), lang="", topics=(r.get("tags") or [])[:5], created=r.get("createdAt")))
    for r in producthunt(os.getenv("PRODUCTHUNT_TOKEN")):
        items.append(dict(id=f"ph:{r['id']}", src="ProductHunt", name=r["name"], desc=r.get("tagline") or "", url=r["url"], score=r.get("votesCount", 0), lang="", topics=[], created=r.get("createdAt")))
    return items

def tg(method, body):
    return requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/{method}", json=body, timeout=30).json()
def notify(text):
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        try: tg("sendMessage", {"chat_id": os.getenv("TELEGRAM_CHAT_ID"), "text": text, "disable_web_page_preview": True})
        except Exception: pass

def gemini(prompt):
    model = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
    for i in range(3):
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", timeout=90,
            headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", "")},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}})
        if r.status_code == 429: time.sleep(20 * (i + 1)); continue
        r.raise_for_status()
        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    raise RuntimeError("Gemini rate limit")

def pitch(it):
    readme = ""
    if it["src"] == "GitHub":
        try:
            r = requests.get(f"https://api.github.com/repos/{it['name']}/readme", headers={**UA, "Accept": "application/vnd.github.raw"}, timeout=15)
            if r.ok: readme = r.text[:1200]
        except Exception: pass
    return gemini(f"""You write for a developer-focused Telegram channel.
Project: {it['name']} ({it['src']})
Description: {it['desc']}
Score: {it['score']} | Language: {it['lang']}
README: {readme}
Return ONLY JSON: {{"hook":"max 8 words","blurb":"one plain sentence, max 22 words, why it matters","post":"Telegram post in plain text, max 650 characters: a scroll-stopping hook line, 2 short sentences on what it does, 3 bullets starting with •, one question to spark comments, 3-4 hashtags. No URL. Never invent features."}}""")

def pick(items, posted, n):
    fresh = sorted([x for x in items if x["id"] not in posted], key=lambda x: -x["score"]); out, seen = [], set()
    for x in fresh:
        if len(out) >= n: break
        if x["src"] not in seen: out.append(x); seen.add(x["src"])
    for x in fresh:
        if len(out) >= n: break
        if x not in out: out.append(x)
    return out

def main(post=False):
    items = collect()
    if not items: print("Nothing fetched, keeping the old feed"); return
    posted = jload(STATE, {"posted": {}}).get("posted", {}); done = []
    for x in items:
        if x["id"] in posted: x["blurb"] = posted[x["id"]]["b"]
    chan = os.getenv("TELEGRAM_CHANNEL_ID")
    if post and chan and os.getenv("GEMINI_API_KEY") and os.getenv("TELEGRAM_BOT_TOKEN"):
        for it in pick(items, posted, int(os.getenv("AUTOPOST_COUNT") or 3)):
            try:
                p = pitch(it)
                kb = [[{"text": "Open project", "url": it["url"]}]]
                if os.getenv("SITE_URL"): kb.append([{"text": "Browse all trending", "url": os.getenv("SITE_URL")}])
                j = tg("sendMessage", {"chat_id": chan, "text": f"{p['post']}\n\n{it['url']}", "reply_markup": {"inline_keyboard": kb}})
                if not j.get("ok"): raise RuntimeError(j.get("description"))
                posted[it["id"]] = {"t": int(time.time()), "b": p["blurb"]}; it["blurb"] = p["blurb"]; done.append(it["name"]); time.sleep(3)
            except Exception as e:
                notify(f"Autopost failed for {it['name']}: {e}"); break
    keep = dict(sorted(posted.items(), key=lambda kv: -kv[1]["t"])[:150])
    FEED.parent.mkdir(exist_ok=True)
    FEED.write_text(json.dumps({"items": items, "updated_at": int(time.time() * 1000)}, ensure_ascii=False), "utf-8")
    STATE.write_text(json.dumps({"posted": keep}, ensure_ascii=False), "utf-8")
    print(f"{len(items)} items, posted: {done}")
    if post: notify("Scan complete. Posted to channel: " + (", ".join(done) or "nothing new"))

if __name__ == "__main__":
    a = sys.argv
    main("--post" in a and a[a.index("--post") + 1].lower() not in ("false", "0", ""))
