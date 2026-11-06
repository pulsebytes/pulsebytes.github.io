Pulsebyte (GitHub edition, no database)
1. Install Git and the GitHub CLI once:  winget install --id Git.Git -e   and   winget install --id GitHub.cli -e
2. Double-click run.cmd. First run opens .env: fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY (and TELEGRAM_CHANNEL_ID for autopost).
3. The script creates a public GitHub repo, stores your keys as encrypted GitHub secrets, enables Pages, and starts the first scan.
   GitHub Actions then scans every 6 hours, writes data/feed.json and autoposts to your channel. The website reads that file.
4. Your laptop app (http://127.0.0.1:8765) handles Telegram commands (send /help to the bot) and makes cards and videos.
run.cmd deploy  = re-save secrets and push changes.  Add your bot as ADMIN of the channel for autopost.
