import os, json, time, threading, subprocess, requests
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
LOCAL = ROOT / "local"; OUT = LOCAL / "out"; OUT.mkdir(parents=True, exist_ok=True)
DB = LOCAL / "drafts.json"; lock = threading.RLock()
TREND = {"items": [], "updated_at": 0, "_t": 0}
from . import ai, render
from scanner import scan as sc

def load(): return json.loads(DB.read_text("utf-8")) if DB.exists() else {}
def save(x): DB.write_text(json.dumps(x, ensure_ascii=False, indent=1), "utf-8")
CHAT = lambda: os.getenv("TELEGRAM_CHAT_ID")
def tg(method, data=None, files=None):
    return requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/{method}", data=data, files=files, timeout=180)
def say(t): tg("sendMessage", {"chat_id": CHAT(), "text": t, "disable_web_page_preview": "true"})

def feed():
    repo = os.getenv("GITHUB_REPO")
    if repo:
        try:
            r = requests.get(f"https://raw.githubusercontent.com/{repo}/main/data/feed.json", timeout=20)
            if r.ok and r.json().get("items"): return r.json()
        except Exception: pass
    return None
def trend(refresh=False):
    global TREND
    if refresh or not TREND["items"]:
        d = None if refresh else feed()
        if not d: d = {"items": sc.collect(), "updated_at": int(time.time() * 1000)}
        TREND = {**d, "_t": time.time()}
    return TREND
def listing(items): return "\n".join(f"{i + 1}. [{x['src']}] {x['name']} ({x['score']})" for i, x in enumerate(items[:25])) or "Nothing yet. Send /scan"
def dispatch(post=True):
    repo = os.getenv("GITHUB_REPO")
    if not repo: return False, "GITHUB_REPO is not set. Run: run.cmd deploy"
    try:
        r = subprocess.run(["gh", "workflow", "run", "scan.yml", "--repo", repo, "-f", "post=" + ("true" if post else "false")], capture_output=True)
        return r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace").strip()
    except FileNotFoundError: return False, "GitHub CLI (gh) not found"

def make_draft(item, note="", did=None):
    c = ai.write(item, note)
    with lock:
        ds = load(); did = did or str(max([int(k) for k in ds] + [0]) + 1)
        d = {**ds.get(did, {}), **c, "id": did, "item": item}
        (OUT / did).mkdir(exist_ok=True)
        d["card"] = f"{did}/card.png"; render.card(d, str(OUT / d["card"]))
        d.pop("video", None); ds[did] = d; save(ds)
    return d

def make_video(did):
    d = load()[did]; render.video(d, str(OUT / did))
    with lock: ds = load(); ds[did]["video"] = f"{did}/short.mp4"; save(ds)
    return ds[did]

def send_draft(d):
    kb = json.dumps({"inline_keyboard": [[{"text": "Regenerate", "callback_data": f"regen:{d['id']}"}, {"text": "Make video", "callback_data": f"video:{d['id']}"}]]})
    with open(OUT / d["card"], "rb") as f:
        tg("sendPhoto", {"chat_id": CHAT(), "caption": f"Draft #{d['id']}: {d['yt_title']}", "reply_markup": kb}, {"photo": f})
    say(f"FACEBOOK POST (draft #{d['id']}):\n\n{d['facebook']}")

def send_video(d):
    with open(OUT / d["video"], "rb") as f:
        tg("sendVideo", {"chat_id": CHAT(), "caption": f"#{d['id']} {d['yt_title']}\n\n{d['yt_description']}"[:1024]}, {"video": f})

# ---- Telegram commands, handled by this laptop app (long polling, no server needed) ----
HELP = ("/scan - scan all sources now\n/autopost - scan on GitHub and post top picks to the channel\n/trending - show the list\n/generate N - create post and card for item N\n"
        "/edit ID text - rewrite draft ID\n/video ID - make Shorts video\n/drafts - list drafts\n/status - is the laptop online?\n\nCommands work while the Pulsebyte app is open.")
def on_update(u):
    try:
        cb = u.get("callback_query"); m = u.get("message") or {}
        chat = str(((cb or {}).get("message") or {}).get("chat", {}).get("id") or m.get("chat", {}).get("id"))
        if chat != str(CHAT()): return
        if cb:
            a, i = cb["data"].split(":"); tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Working..."})
            if a == "regen": send_draft(make_draft(load()[i]["item"], "Rewrite with a completely fresh angle and a new hook", i))
            else: send_video(make_video(i))
            return
        p = (m.get("text") or "").split(); cmd = p[0].split("@")[0].lower() if p else ""; a = p[1:]
        if cmd == "/scan": say("Scanning..."); say(listing(trend(True)["items"]))
        elif cmd == "/autopost":
            ok, msg = dispatch(True); say("Autopost started on GitHub. Posts appear in the channel in a minute or two." if ok else "Could not start: " + msg)
        elif cmd == "/trending": say(listing(trend()["items"]))
        elif cmd == "/generate":
            items = trend()["items"]; n = int(a[0]) - 1
            if not 0 <= n < len(items): return say("Pick a number from /trending")
            say("Writing: " + items[n]["name"]); send_draft(make_draft(items[n]))
        elif cmd == "/edit" and a: send_draft(make_draft(load()[a[0]]["item"], " ".join(a[1:]) or "Improve it", a[0]))
        elif cmd == "/video" and a: say("Making the video, about a minute..."); send_video(make_video(a[0]))
        elif cmd == "/drafts": say("\n".join(f"#{k} {v['item']['name']}" for k, v in load().items()) or "No drafts yet")
        elif cmd == "/status": say("Laptop app is online")
        else: say(HELP)
    except Exception as e: say(f"Failed: {e}")

def poller():
    if not os.getenv("TELEGRAM_BOT_TOKEN"): return
    try: tg("deleteWebhook", {})
    except Exception: pass
    off = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/getUpdates", params={"offset": off, "timeout": 30}, timeout=45).json()
            if not r.get("ok"): print("telegram:", r); time.sleep(10); continue
            for u in r["result"]:
                off = u["update_id"] + 1; threading.Thread(target=on_update, args=(u,), daemon=True).start()
        except Exception as e: print("telegram poll error:", e); time.sleep(5)

@asynccontextmanager
async def life(_):
    threading.Thread(target=poller, daemon=True).start(); yield

app = FastAPI(lifespan=life)
app.mount("/files", StaticFiles(directory=OUT), name="files")

@app.get("/favicon.ico")
def fav(): return Response(status_code=204)
@app.get("/")
def index(): return FileResponse(Path(__file__).parent / "static" / "index.html")
@app.get("/api/trending")
def trending(): return trend()
@app.post("/api/scan")
def scan(): return trend(True)
@app.post("/api/autopost")
def autopost():
    ok, msg = dispatch(True)
    if not ok: raise HTTPException(500, msg)
    return {"ok": True}
@app.get("/api/drafts")
def drafts(): return list(reversed(list(load().values())))
@app.post("/api/generate")
def generate(b: dict = Body(...)):
    it = next((x for x in trend()["items"] if x["id"] == b["id"]), None)
    if not it: raise HTTPException(404, "Item not found, refresh the list")
    return make_draft(it)
@app.post("/api/edit")
def edit(b: dict = Body(...)):
    d = load()[b["id"]]; return make_draft(d["item"], b.get("text") or "Rewrite with a fresh angle", b["id"])
@app.post("/api/video/{did}")
def video(did: str): return make_video(did)
@app.post("/api/telegram/{did}")
def to_tg(did: str):
    d = load()[did]; send_draft(d)
    if d.get("video"): send_video(d)
    return {"ok": True}
@app.post("/api/channel/{did}")
def to_channel(did: str):
    ch = os.getenv("TELEGRAM_CHANNEL_ID")
    if not ch: raise HTTPException(400, "Set TELEGRAM_CHANNEL_ID in .env")
    d = load()[did]
    with open(OUT / d["card"], "rb") as f: tg("sendPhoto", {"chat_id": ch, "caption": d["facebook"][:1000]}, {"photo": f})
    if d.get("video"):
        with open(OUT / d["video"], "rb") as f: tg("sendVideo", {"chat_id": ch, "caption": d["yt_title"]}, {"video": f})
    return {"ok": True}
@app.post("/api/folder/{did}")
def folder(did: str):
    if os.name == "nt": os.startfile(str(OUT / did))
    return {"ok": True}
