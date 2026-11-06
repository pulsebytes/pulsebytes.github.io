import os, json, time, requests

PROMPT = """You are an elite social media strategist and storyteller for developer and tech audiences.
Your goal is MAXIMUM viewer retention and engagement.

Project: {name} (from {src})
Description: {desc}
Score: {score} | Language: {lang} | Topics: {topics}
URL: {url}
README excerpt: {readme}
{note}

Return ONLY valid JSON with these exact keys:

hook: A scroll-stopping, curiosity-gap opening line. Max 8 words. Create urgency or surprise.
card_title: Max 6 words. Bold benefit or intrigue.
card_points: Array of exactly 3 punchy bullets. Max 9 words each. Use action verbs. Lead with the outcome.

facebook: Viral-optimised post, 100-150 words.
  - Line 1: the hook (identical to hook field above)
  - Lines 2-3: 1-sentence problem the project solves
  - Lines 4-6: 2-3 short punchy paragraphs on what it does / why it matters
  - Max 4 emojis, placed naturally
  - End with an open question that invites comments
  - Then a blank line, then the URL
  - Then 4-6 relevant hashtags on one line

yt_title: Curiosity-driven YouTube title, max 70 chars. Use numbers or "how" if natural.
yt_description: Two short punchy paragraphs (what it is, why you need it), then URL, then 6-10 hashtags.

script: Array of EXACTLY 6 narration sentences for a 45-second YouTube Short.
  Structure:
  [0] HOOK  — Shocking stat or question that stops the scroll. Max 15 words.
  [1] PROBLEM — The pain point this solves. Relatable. Max 16 words.
  [2] REVEAL — Introduce the project by name. Max 16 words.
  [3] DEMO   — One powerful feature or use-case in action. Max 18 words.
  [4] PROOF  — Social proof (stars, users, orgs using it) or key benefit. Max 16 words.
  [5] CTA    — Urgent call to action: follow, link in bio, comment. Max 14 words.
  Each sentence must be punchy, conversational, and flow naturally when spoken aloud.

slide_texts: Array of EXACTLY 6 strings, one per slide (matches script order).
  Each is a SHORT on-screen caption (max 6 words) that reinforces the spoken sentence.
  These appear as large text overlaid on the slide background.
  Examples: "Most devs don't know this", "Saves 10 hours a week", "Drop a ⭐ right now"

slide_emojis: Array of EXACTLY 6 single emojis (one per slide) that visually accent each slide.
  Pick emojis relevant to the content, e.g. 🚨 🤯 🛠️ ⚡ 🌟 🔥

Stay truthful: never invent features not in the description or README.
Return ONLY the JSON object, no markdown, no explanation."""

def readme(item):
    if item["src"] != "GitHub": return ""
    try:
        r = requests.get(f"https://api.github.com/repos/{item['name']}/readme", timeout=15,
                         headers={"Accept": "application/vnd.github.raw", "User-Agent": "pulsebyte"})
        return r.text[:2000] if r.ok else ""
    except Exception: return ""

def write(item, note=""):
    p = PROMPT.format(name=item["name"], src=item["src"], desc=item.get("desc", ""),
                      score=item.get("score", 0), lang=item.get("lang", ""),
                      topics=", ".join(item.get("topics", [])), url=item["url"],
                      readme=readme(item), note=("Extra instruction: " + note) if note else "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    for i in range(3):
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.getenv("GEMINI_API_KEY", "")}, timeout=90,
            json={"contents": [{"parts": [{"text": p}]}],
                  "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0}})
        if r.status_code == 429: time.sleep(15 * (i + 1)); continue
        r.raise_for_status()
        return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    raise RuntimeError("Gemini rate limit, try again in a minute")
