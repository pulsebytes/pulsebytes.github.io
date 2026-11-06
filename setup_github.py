import json, shutil, subprocess, sys, time, requests
from pathlib import Path
from dotenv import dotenv_values
ROOT = Path(__file__).parent; ENV = ROOT / ".env"
e = dotenv_values(ENV)

# ── If already deployed and not forced, skip ─────────────────────────────────
mode = next((a for a in sys.argv[1:] if a.startswith("--")), "")
if mode == "--private":
    repo = e.get("GITHUB_REPO", "")
    if not repo: sys.exit("GITHUB_REPO is not set in .env")
    print(f"Making {repo} private...")
    r = subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}", "-f", "private=true"], capture_output=True)
    if r.returncode == 0:
        print(f"Done. {repo} is now private.")
        sys.exit(0)
    else:
        print(r.stderr.decode("utf-8", "replace"))
        sys.exit(1)

if e.get("GITHUB_REPO") and mode not in ("--force", "--orgdeploy"): sys.exit(0)

def setenv(k, v):
    lines = [l for l in ENV.read_text(encoding="utf-8").splitlines() if not l.startswith(k + "=")]
    ENV.write_text("\n".join(lines + [f"{k}={v}"]) + "\n", encoding="utf-8")

def run(args, ok=False, inp=None, cwd=None):
    r = subprocess.run(args, cwd=cwd or ROOT, capture_output=True,
                       input=inp.encode("utf-8") if inp else None)
    so = r.stdout.decode("utf-8", "replace").strip()
    se = r.stderr.decode("utf-8", "replace").strip()
    if r.returncode and not ok: print(so + "\n" + se); sys.exit("Failed: " + " ".join(str(a) for a in args))
    return r.returncode, so, se

def api_gh(method, path, fields=None, ok=False):
    args = ["gh", "api", f"-X{method}", path]
    for f in (fields or []): args += ["-f", f]
    return run(args, ok=ok)

# ── Pre-flight checks ─────────────────────────────────────────────────────────
for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY"):
    if not e.get(k): sys.exit(f"Missing {k} in .env")
if not e.get("TELEGRAM_CHANNEL_ID"):
    print("Note: TELEGRAM_CHANNEL_ID is empty — channel autopost is off.")
if not (shutil.which("git") and shutil.which("gh")):
    sys.exit(
        "Install Git and the GitHub CLI, then open a NEW terminal and run run.cmd again:\n"
        "  winget install --id Git.Git -e\n"
        "  winget install --id GitHub.cli -e"
    )
if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode:
    subprocess.run(["gh", "auth", "login", "-s", "workflow"])
run(["gh", "auth", "setup-git"], ok=True)

# ── Determine owner, repo, URL ────────────────────────────────────────────────
personal_owner = run(["gh", "api", "user", "-q", ".login"])[1]
site_repo      = e.get("SITE_REPO") or "pulsebyte"

if mode == "--orgdeploy":
    # ═══════════════════════════════════════════════════════════════════
    # ORG DEPLOY MODE
    # Creates/uses a "pulsebytes" GitHub organisation, makes a repo
    # named "pulsebytes.github.io" so the site lives at pulsebytes.github.io
    # Also makes the ORIGINAL personal repo private.
    # ═══════════════════════════════════════════════════════════════════
    org  = e.get("SITE_ORG") or "pulsebytes"
    repo = f"{org}.github.io"            # GitHub Pages user/org repo
    full = f"{org}/{repo}"
    url  = f"https://{org}.github.io/"

    print(f"\n── Org deploy mode ──────────────────────────────")
    print(f"   Organisation : {org}")
    print(f"   Repo         : {repo}")
    print(f"   Site URL     : {url}")
    print(f"─────────────────────────────────────────────────\n")

    # 1. Check the org exists, or tell the user to create it
    rc, out, _ = run(["gh", "api", f"orgs/{org}"], ok=True)
    if rc != 0:
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Action required — create the GitHub Organisation first      ║
╠══════════════════════════════════════════════════════════════╣
║  1. Open https://github.com/organizations/plan               ║
║  2. Click "Create a free organisation"                       ║
║  3. Set the organisation name to: {org:<26} ║
║  4. Finish setup, then run:  run.cmd orgdeploy  again        ║
╚══════════════════════════════════════════════════════════════╝
""")
        sys.exit(1)
    print(f"✓ Organisation '{org}' found.")

    # 2. Create the org repo if it doesn't exist
    rc, _, _ = run(["gh", "api", f"repos/{full}"], ok=True)
    if rc != 0:
        print(f"Creating repo {full} ...")
        rc2, so2, se2 = run(["gh", "repo", "create", full,
                              "--public", "--description", "Pulsebyte – trending dev projects"], ok=True)
        if rc2 != 0:
            print(so2, se2)
            sys.exit(f"Could not create repo {full}. Make sure your account is a member of the org '{org}'.")
        print(f"✓ Repo {full} created.")
    else:
        print(f"✓ Repo {full} already exists.")

    # 3. Make the ORIGINAL personal repo private (if it exists and is different)
    old_full = e.get("GITHUB_REPO", "")
    if old_full and old_full != full:
        print(f"Making {old_full} private ...")
        run(["gh", "api", "-X", "PATCH", f"repos/{old_full}",
             "-f", "private=true"], ok=True)
        print(f"✓ {old_full} is now private.")

    # 4. Add org remote and push docs/ as the site
    print("Pushing site to org repo ...")
    run(["git", "remote", "remove", "org"], ok=True)
    org_remote = f"https://github.com/{full}.git"
    run(["git", "remote", "add", "org", org_remote])
    run(["git", "push", "org", "main", "--force"])
    print(f"✓ Code pushed to {full}.")

    # 5. Enable GitHub Pages (root of main for user/org repos)
    print("Enabling GitHub Pages on org repo ...")
    pg = ["-f", "source[branch]=main", "-f", "source[path]=/docs"]
    if run(["gh", "api", "-X", "POST", f"repos/{full}/pages", *pg], ok=True)[0]:
        run(["gh", "api", "-X", "PUT",  f"repos/{full}/pages", *pg], ok=True)
    print("✓ GitHub Pages enabled.")

    # 6. Store secrets on org repo
    print("Saving secrets to org repo ...")
    e = dotenv_values(ENV)
    for n in ("GEMINI_API_KEY","GEMINI_MODEL","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID",
              "TELEGRAM_CHANNEL_ID","AUTOPOST_COUNT","SITE_URL","PRODUCTHUNT_TOKEN"):
        if e.get(n): run(["gh", "secret", "set", n, "--repo", full], inp=e[n])

    # 7. Update config.js and .env with new URLs
    cfg = {
        "api":     f"https://raw.githubusercontent.com/{full}/main/data/feed.json",
        "channel": e.get("TELEGRAM_CHANNEL_LINK", ""),
    }
    # Preserve existing social keys from config.js if present
    cfg_path = ROOT / "docs" / "config.js"
    if cfg_path.exists():
        try:
            existing_text = cfg_path.read_text(encoding="utf-8")
            start = existing_text.find("{")
            end   = existing_text.rfind("}") + 1
            existing = json.loads(existing_text[start:end])
            for k in ("telegram","youtube","twitter","facebook","instagram","tiktok","github",
                      "site_name","tagline"):
                if existing.get(k): cfg[k] = existing[k]
        except Exception: pass
    cfg_path.write_text("window.PULSEBYTE = " + json.dumps(cfg, indent=2) + ";\n", encoding="utf-8")
    setenv("SITE_URL",    url)
    setenv("SITE_ORG",    org)
    setenv("GITHUB_REPO", full)

    # 8. Trigger first scan on org repo
    print("Triggering first scan on org repo ...")
    for _ in range(6):
        if run(["gh", "workflow", "run", "scan.yml", "--repo", full, "-f", "post=false"], ok=True)[0] == 0: break
        time.sleep(5)

    try: requests.post(f"https://api.telegram.org/bot{e['TELEGRAM_BOT_TOKEN']}/deleteWebhook", timeout=20)
    except Exception: pass

    print(f"\n✅ Done! Your site will be live in ~1 minute at: {url}")
    print(f"   (GitHub Pages rebuild takes about 60 seconds)\n")
    sys.exit(0)

# ═══════════════════════════════════════════════════════════════════
# STANDARD PERSONAL DEPLOY MODE (unchanged behaviour)
# ═══════════════════════════════════════════════════════════════════
owner = personal_owner
full  = f"{owner}/{site_repo}"
url   = f"https://{owner}.github.io/{site_repo}/"

# Preserve existing social links in config.js
cfg = {"api": f"https://raw.githubusercontent.com/{full}/main/data/feed.json",
       "channel": e.get("TELEGRAM_CHANNEL_LINK", "")}
cfg_path = ROOT / "docs" / "config.js"
if cfg_path.exists():
    try:
        existing_text = cfg_path.read_text(encoding="utf-8")
        start = existing_text.find("{"); end = existing_text.rfind("}") + 1
        existing = json.loads(existing_text[start:end])
        for k in ("telegram","youtube","twitter","facebook","instagram","tiktok","github",
                  "site_name","tagline"):
            if existing.get(k): cfg[k] = existing[k]
    except Exception: pass
cfg_path.write_text("window.PULSEBYTE = " + json.dumps(cfg, indent=2) + ";\n", encoding="utf-8")
setenv("SITE_URL", url)

if not (ROOT / ".git").exists(): run(["git", "init", "-b", "main"])
if not run(["git", "config", "user.name"], ok=True)[1]:
    run(["git", "config", "user.name", owner])
    run(["git", "config", "user.email", f"{owner}@users.noreply.github.com"])
run(["git", "add", "-A"]); run(["git", "commit", "-m", "Pulsebyte"], ok=True)
if "origin" not in run(["git", "remote"], ok=True)[1]:
    run(["gh", "repo", "create", full, "--public", "--source=.", "--remote=origin"])
setenv("GITHUB_REPO", full)

e = dotenv_values(ENV); print("Saving secrets to GitHub...")
for n in ("GEMINI_API_KEY","GEMINI_MODEL","TELEGRAM_BOT_TOKEN","TELEGRAM_CHAT_ID",
          "TELEGRAM_CHANNEL_ID","AUTOPOST_COUNT","SITE_URL","PRODUCTHUNT_TOKEN"):
    if e.get(n): run(["gh", "secret", "set", n, "--repo", full], inp=e[n])

print("Pushing code...")
rc, so, se = run(["git", "push", "-u", "origin", "main"], ok=True)
if rc and "workflow" in (so + se).lower():
    subprocess.run(["gh", "auth", "refresh", "-h", "github.com", "-s", "workflow"])
    rc, so, se = run(["git", "push", "-u", "origin", "main"], ok=True)
if rc: print(so + "\n" + se); sys.exit("git push failed")

print("Enabling GitHub Pages...")
pg = ["-f", "source[branch]=main", "-f", "source[path]=/docs"]
if run(["gh", "api", "-X", "POST", f"repos/{full}/pages", *pg], ok=True)[0]:
    run(["gh", "api", "-X", "PUT", f"repos/{full}/pages", *pg], ok=True)

print("Starting the first scan on GitHub...")
for _ in range(6):
    if run(["gh", "workflow", "run", "scan.yml", "--repo", full, "-f", "post=false"], ok=True)[0] == 0: break
    time.sleep(5)
try: requests.post(f"https://api.telegram.org/bot{e['TELEGRAM_BOT_TOKEN']}/deleteWebhook", timeout=20)
except Exception: pass
print("Done. Site (live in about a minute):", url)
