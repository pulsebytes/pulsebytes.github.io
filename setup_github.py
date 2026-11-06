import json, shutil, subprocess, sys, time, requests
from pathlib import Path
from dotenv import dotenv_values
ROOT = Path(__file__).parent; ENV = ROOT / ".env"
e = dotenv_values(ENV)
if e.get("GITHUB_REPO") and "--force" not in sys.argv: sys.exit(0)

def setenv(k, v):
    lines = [l for l in ENV.read_text(encoding="utf-8").splitlines() if not l.startswith(k + "=")]
    ENV.write_text("\n".join(lines + [f"{k}={v}"]) + "\n", encoding="utf-8")
def run(args, ok=False, inp=None):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, input=inp.encode("utf-8") if inp else None)
    so, se = r.stdout.decode("utf-8", "replace").strip(), r.stderr.decode("utf-8", "replace").strip()
    if r.returncode and not ok: print(so + "\n" + se); sys.exit("Failed: " + " ".join(args))
    return r.returncode, so, se

for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY"):
    if not e.get(k): sys.exit(f"Missing {k} in .env")
if not e.get("TELEGRAM_CHANNEL_ID"): print("Note: TELEGRAM_CHANNEL_ID is empty, channel autopost is off.")
if not (shutil.which("git") and shutil.which("gh")):
    sys.exit("Install Git and the GitHub CLI, then open a NEW terminal and run run.cmd again:\n  winget install --id Git.Git -e\n  winget install --id GitHub.cli -e")
if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode: subprocess.run(["gh", "auth", "login", "-s", "workflow"])
run(["gh", "auth", "setup-git"], ok=True)
owner = run(["gh", "api", "user", "-q", ".login"])[1]; repo = e.get("SITE_REPO") or "pulsebyte"; full = f"{owner}/{repo}"
url = f"https://{owner}.github.io/{repo}/"
(ROOT / "docs" / "config.js").write_text("window.PULSEBYTE = " + json.dumps({"api": f"https://raw.githubusercontent.com/{full}/main/data/feed.json", "channel": e.get("TELEGRAM_CHANNEL_LINK", "")}) + ";\n", encoding="utf-8")
setenv("SITE_URL", url)

if not (ROOT / ".git").exists(): run(["git", "init", "-b", "main"])
if not run(["git", "config", "user.name"], ok=True)[1]:
    run(["git", "config", "user.name", owner]); run(["git", "config", "user.email", f"{owner}@users.noreply.github.com"])
run(["git", "add", "-A"]); run(["git", "commit", "-m", "Pulsebyte"], ok=True)
if "origin" not in run(["git", "remote"], ok=True)[1]: run(["gh", "repo", "create", full, "--public", "--source=.", "--remote=origin"])
setenv("GITHUB_REPO", full)

e = dotenv_values(ENV); print("Saving secrets to GitHub...")
for n in ("GEMINI_API_KEY", "GEMINI_MODEL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID", "AUTOPOST_COUNT", "SITE_URL", "PRODUCTHUNT_TOKEN"):
    if e.get(n): run(["gh", "secret", "set", n, "--repo", full], inp=e[n])

print("Pushing code...")
rc, so, se = run(["git", "push", "-u", "origin", "main"], ok=True)
if rc and "workflow" in (so + se).lower():
    subprocess.run(["gh", "auth", "refresh", "-h", "github.com", "-s", "workflow"]); rc, so, se = run(["git", "push", "-u", "origin", "main"], ok=True)
if rc: print(so + "\n" + se); sys.exit("git push failed")

print("Enabling GitHub Pages...")
pg = ["-f", "source[branch]=main", "-f", "source[path]=/docs"]
if run(["gh", "api", "-X", "POST", f"repos/{full}/pages", *pg], ok=True)[0]: run(["gh", "api", "-X", "PUT", f"repos/{full}/pages", *pg], ok=True)

print("Starting the first scan on GitHub...")
for _ in range(6):
    if run(["gh", "workflow", "run", "scan.yml", "--repo", full, "-f", "post=false"], ok=True)[0] == 0: break
    time.sleep(5)
try: requests.post(f"https://api.telegram.org/bot{e['TELEGRAM_BOT_TOKEN']}/deleteWebhook", timeout=20)
except Exception: pass
print("Done. Site (live in about a minute):", url)
