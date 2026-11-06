import os, json, time, requests

PROMPT = """You are a top social media copywriter for developer and tech audiences.
Project: {name} (from {src})
Description: {desc}
Score: {score} | Language: {lang} | Topics: {topics}
URL: {url}
README excerpt: {readme}
{note}
Return ONLY JSON with these keys:
hook: scroll-stopping line, max 8 words
card_title: max 6 words
card_points: array of 3 punchy bullets, max 9 words each
facebook: engaging post, 80-140 words, hook as first line, short paragraphs, max 4 emojis, ends with a question to spark comments, then the URL, then 3-5 hashtags
yt_title: curiosity-driven, max 70 characters
yt_description: 2 short paragraphs, then the URL, then hashtags
script: array of 4 narration sentences for a 25 second Short, max 18 words each; first is the hook, last is a call to action
Stay truthful: never invent features that are not in the description or README."""

def readme(item):
    if item["src"] != "GitHub": return ""
    try:
        r = requests.get(f"https://api.github.com/repos/{item['name']}/readme", timeout=15,
                         headers={"Accept": "application/vnd.github.raw", "User-Agent": "pulsebyte"})
        return r.text[:1500] if r.ok else ""
    except Exception: return ""

def write(item, note=""):
    p = PROMPT.format(name=item["name"], src=item["src"], desc=item.get("desc", ""), score=item.get("score", 0),
                      lang=item.get("lang", ""), topics=", ".join(item.get("topics", [])), url=item["url"],
                      readme=readme(item), note=("Extra instruction: " + note) if note else "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    for i in range(3):
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", "")}, timeout=90,
            json={"contents": [{"parts": [{"text": p}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}})
        if r.status_code == 429: time.sleep(15 * (i + 1)); continue
        r.raise_for_status()
        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    raise RuntimeError("Gemini rate limit, try again in a minute")
