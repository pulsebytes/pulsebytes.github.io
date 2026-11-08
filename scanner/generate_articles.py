"""Static Article Generator for Pulsebyte.
Generates self-contained static HTML pages in docs/articles/<slug>.html and
high-resolution 1200x630 OpenGraph social preview cards in docs/assets/cards/<slug>.png.
Ensures 100% accurate social media preview cards on X/Twitter, Facebook, LinkedIn, Telegram, and WhatsApp.
"""
import os
import sys
import json
import html
import re
import urllib.parse
from datetime import datetime, timezone
import email.utils
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARTICLES_DIR = DOCS / "articles"
ARTICLES_FILE = DOCS / "articles.json"
ARTICLE_TEMPLATE_FILE = DOCS / "article.html"
ARTICLE_CSS_FILE = DOCS / "article.css"
CARDS_DIR = DOCS / "assets" / "cards"

SITE_URL = os.getenv("SITE_URL", "https://pulsebytes.github.io").rstrip("/")

def parse_date(val):
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, (int, float)):
        if val > 1e11: val /= 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            f = float(val)
            if f > 1e11: f /= 1000.0
            return datetime.fromtimestamp(f, tz=timezone.utc)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)

def format_human_date(dt):
    return dt.strftime("%b %d, %Y")

def extract_styles():
    if ARTICLE_CSS_FILE.exists():
        return ARTICLE_CSS_FILE.read_text("utf-8")
    if ARTICLE_TEMPLATE_FILE.exists():
        text = ARTICLE_TEMPLATE_FILE.read_text("utf-8")
        m = re.search(r"<style>(.*?)</style>", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""

STYLES = extract_styles()

def get_font(size, bold=True):
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    font_candidates = [
        # Windows
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        # Linux / Ubuntu
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        # macOS
        "/System/Library/Fonts/SFProText-Bold.otf" if bold else "/System/Library/Fonts/SFProText-Regular.otf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def wrap_text(draw, text, font, max_width):
    lines = []
    for w in (text or "").split():
        test = (lines[-1] + " " + w) if lines else w
        if not lines or draw.textlength(test, font=font) <= max_width:
            if lines:
                lines[-1] = test
            else:
                lines.append(w)
        else:
            lines.append(w)
    return lines

def generate_social_card(art, out_path):
    """Generates a high-resolution 1200x630 social preview card for this specific article."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print(f"PIL not installed; skipping social card generation for {out_path.name}")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (9, 13, 22))

    # Background Gradient
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / float(H)
        r = int(9 + (15 - 9) * t)
        g = int(13 + (23 - 13) * t)
        b = int(22 + (42 - 22) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Ambient Accent Glows
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([1050 - 280, 100 - 280, 1050 + 280, 100 + 280], fill=(99, 102, 241, 38))
    od.ellipse([120 - 220, 520 - 220, 120 + 220, 520 + 220], fill=(56, 189, 248, 26))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)

    # 1. Top Brand Row
    # Pulse logo mark
    d.rounded_rectangle([60, 48, 106, 94], radius=11, fill=(99, 102, 241))
    scale = 0.55
    cx, cy = 83, 71
    pts = [
        (cx - 24 * scale, cy), (cx - 13 * scale, cy), (cx - 8 * scale, cy + 8 * scale),
        (cx - 2 * scale, cy - 22 * scale), (cx + 5 * scale, cy + 18 * scale),
        (cx + 11 * scale, cy - 8 * scale), (cx + 16 * scale, cy), (cx + 24 * scale, cy)
    ]
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=(255, 255, 255), width=3)

    f_logo = get_font(26, True)
    d.text((120, 55), "Pulsebyte", font=f_logo, fill=(255, 255, 255))

    # Badge Pill
    f_badge = get_font(13, True)
    d.rounded_rectangle([255, 55, 395, 87], radius=7, fill=(30, 27, 75), outline=(129, 140, 248), width=1)
    d.text((269, 63), "TECHNICAL BREAKDOWN", font=f_badge, fill=(165, 180, 252))

    # Project Source Chip (Right side)
    item = art.get("item") or {}
    p_name = item.get("name") or ""
    p_src = item.get("src") or "Open Source"
    p_score = str(item.get("score") or "")
    p_lang = item.get("lang") or ""

    right_text = f"{p_src}: {p_name}" if p_name else "Architecture Breakdown"
    if p_score and p_score != "0":
        right_text += f"  ★ {p_score}"
    if p_lang:
        right_text += f" · {p_lang}"

    f_proj = get_font(15, True)
    w_proj = int(d.textlength(right_text, font=f_proj))
    d.rounded_rectangle([1140 - w_proj - 28, 52, 1140, 90], radius=8, fill=(20, 30, 48), outline=(51, 65, 85), width=1)
    d.text((1140 - w_proj - 14, 61), right_text, font=f_proj, fill=(203, 213, 225))

    # 2. Article Title (Auto-fit typography)
    title = art.get("title") or "Technical Deep Dive"
    f_sz = 44
    f_title = get_font(f_sz, True)
    t_lines = wrap_text(d, title, f_title, 1080)
    if len(t_lines) > 3:
        f_sz = 38
        f_title = get_font(f_sz, True)
        t_lines = wrap_text(d, title, f_title, 1080)

    y = 150
    for l in t_lines[:3]:
        # Drop shadow
        d.text((62, y + 2), l, font=f_title, fill=(0, 0, 0))
        d.text((60, y), l, font=f_title, fill=(255, 255, 255))
        y += int(f_sz * 1.32)

    # 3. Article Excerpt / TL;DR
    tldr = art.get("tldr") or art.get("excerpt") or ""
    if tldr:
        f_tldr = get_font(21, False)
        t_tldr = wrap_text(d, tldr, f_tldr, 1080)
        y = max(y + 24, 380)
        for l in t_tldr[:3]:
            d.text((60, y), l, font=f_tldr, fill=(148, 163, 184))
            y += 33

    # 4. Bottom Footer Bar
    d.line([(60, 545), (1140, 545)], fill=(30, 41, 59), width=1)

    slug = art.get("slug") or art.get("id") or "article"
    canonical = f"pulsebytes.github.io/articles/{slug}.html"
    f_url = get_font(18, True)
    d.text((60, 568), "⚡ " + canonical, font=f_url, fill=(56, 189, 248))

    read_time = art.get("read_time") or "4 min read"
    r_text = f"⏱️ {read_time}  ·  Verified Analysis"
    f_rt = get_font(18, True)
    w_rt = int(d.textlength(r_text, font=f_rt))
    d.text((1140 - w_rt, 568), r_text, font=f_rt, fill=(251, 191, 36))

    im.save(out_path, "PNG", optimize=True)
    return True

def generate_article_page(art, all_articles, styles=STYLES):
    slug = art.get("slug") or art.get("id") or "article"
    title = art.get("title") or "Technical Breakdown"
    tldr = art.get("tldr") or art.get("excerpt") or ""
    content = art.get("content") or ""
    tags = art.get("tags") or []
    read_time = art.get("read_time") or "4 min read"
    item = art.get("item") or {}

    pub_dt = parse_date(art.get("published_at") or art.get("date") or art.get("created_at"))
    iso_date = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    human_date = format_human_date(pub_dt)

    canonical_url = f"{SITE_URL}/articles/{slug}.html"
    card_url = f"{SITE_URL}/assets/cards/{slug}.png"

    esc_title = html.escape(title)
    esc_tldr = html.escape(tldr)
    json_title = json.dumps(title)
    json_tldr = json.dumps(tldr)
    json_body = json.dumps(re.sub(r"<[^>]+>", " ", content)[:1000])

    tags_html = "".join(f'<span class="reader-tag">#{html.escape(t)}</span>' for t in tags)
    tags_meta = "\n".join(f'  <meta property="article:tag" content="{html.escape(t)}">' for t in tags)

    # Repository avatar & details
    p_name = html.escape(item.get("name") or "")
    p_url = html.escape(item.get("url") or "#")
    p_src = html.escape(item.get("src") or "Open Source")
    p_score = html.escape(str(item.get("score") or ""))
    p_lang = html.escape(item.get("lang") or "")
    p_desc = html.escape(item.get("desc") or "")

    owner = (item.get("name") or "").split("/")[0] or ""
    if item.get("src") == "GitHub" and owner:
        avatar_url = f"https://github.com/{urllib.parse.quote(owner)}.png?size=100"
    else:
        avatar_url = f"https://api.dicebear.com/8.x/identicon/svg?seed={urllib.parse.quote(p_name or 'pb')}"

    # Featured project showcase banner
    project_html = ""
    if p_name or p_url != "#":
        project_html = f"""
      <div class="reader-project-banner">
        <img src="{avatar_url}" class="reader-project-avatar" alt="{p_name}" onerror="this.style.display='none'">
        <div class="rpb-details">
          <div class="rpb-title">
            <span class="art-badge">{p_src}</span>
            <strong>{p_name}</strong>
          </div>
          <div class="rpb-desc">{p_desc} &middot; <span style="color:var(--hot)">★ {p_score}</span> &middot; {p_lang}</div>
        </div>
        <a class="btn p sm" href="{p_url}" target="_blank" rel="noopener noreferrer">View Repository &rarr;</a>
      </div>
"""

    # Sidebar project card
    sidebar_project_html = ""
    if p_name or p_url != "#":
        sidebar_project_html = f"""
      <div class="sidebar-box" id="sidebar-project-box">
        <div class="sidebar-box-title">Featured Repository</div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <img src="{avatar_url}" style="width:34px;height:34px;border-radius:8px;border:1px solid var(--line)" alt="" onerror="this.style.display='none'">
          <div>
            <strong style="font-size:13.5px;color:var(--ink);display:block">{p_name}</strong>
            <span style="font-size:11.5px;color:var(--ink3)">★ {p_score} stars &middot; {p_lang}</span>
          </div>
        </div>
        <p style="font-size:12px;color:var(--ink2);line-height:1.45;margin-bottom:12px">{p_desc}</p>
        <a class="btn p sm" href="{p_url}" target="_blank" rel="noopener noreferrer" style="width:100%;justify-content:center">
          Open Repository &rarr;
        </a>
      </div>
"""

    # Recommendation grid of other articles
    other_articles = [a for a in all_articles if (a.get("slug") != slug and a.get("id") != art.get("id"))][:3]
    more_cards = []
    for oa in other_articles:
        oa_slug = oa.get("slug") or oa.get("id")
        oa_url = f"{oa_slug}.html"
        more_cards.append(f"""
          <a class="more-card" href="{oa_url}">
            <div style="font-size:11.5px;color:var(--ink3);margin-bottom:6px">{html.escape(oa.get('read_time','4 min read'))}</div>
            <h4 style="font-size:14px;font-weight:700;color:var(--ink);margin-bottom:6px;line-height:1.35">{html.escape(oa.get('title',''))}</h4>
            <p style="font-size:12.5px;color:var(--ink2);margin-bottom:10px">{html.escape(oa.get('tldr','') or oa.get('excerpt',''))}</p>
            <span>Read breakdown &rarr;</span>
          </a>
""")
    more_html = "".join(more_cards)

    page_html = f"""<!doctype html>
<html lang="en" data-theme="dark" prefix="og: https://ogp.me/ns# fb: https://ogp.me/ns/fb#">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>{esc_title} – Pulsebyte</title>
<meta name="description" content="{esc_tldr}">
<meta name="robots" content="index, follow">
<meta name="author" content="Pulsebyte Editorial">
<link rel="canonical" href="{canonical_url}">

<!-- Open Graph / Facebook -->
<meta property="og:type" content="article">
<meta property="og:site_name" content="Pulsebyte">
<meta property="og:title" content="{esc_title}">
<meta property="og:description" content="{esc_tldr}">
<meta property="og:url" content="{canonical_url}">
<meta property="og:image" content="{card_url}">
<meta property="og:image:secure_url" content="{card_url}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc_title}">
<meta property="og:locale" content="en_US">
<meta property="article:published_time" content="{iso_date}">
<meta property="article:author" content="Pulsebyte Editorial">
{tags_meta}

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@Pulsebyte">
<meta name="twitter:title" content="{esc_title}">
<meta name="twitter:description" content="{esc_tldr}">
<meta name="twitter:image" content="{card_url}">
<meta name="twitter:image:alt" content="{esc_title}">

<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="../favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="../favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="../apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="Pulsebyte · RSS Feed" href="../feed.xml">
<link rel="alternate" type="application/atom+xml" title="Pulsebyte · Atom Feed" href="../atom.xml">
<link rel="stylesheet" href="../article.css">

<!-- Structured Data for Search Engines & Medium Story Importer -->
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{canonical_url}"
  }},
  "headline": {json_title},
  "description": {json_tldr},
  "articleBody": {json_body},
  "image": "{card_url}",
  "datePublished": "{iso_date}",
  "dateModified": "{iso_date}",
  "author": {{
    "@type": "Organization",
    "name": "Pulsebyte Editorial",
    "url": "{SITE_URL}"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "Pulsebyte",
    "logo": {{
      "@type": "ImageObject",
      "url": "{SITE_URL}/assets/logo.png"
    }}
  }}
}}
</script>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<script>(function(){{var t=localStorage.getItem("pb-theme")||(matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");document.documentElement.dataset.theme=t}})();</script>

<style>
{styles}
</style>
</head>
<body>

<!-- ══ HEADER ══ -->
<header role="banner">
  <a class="logo" href="../">
    <div class="logo-mark">
      <svg width="16" height="16" viewBox="0 0 32 32" fill="none">
        <path d="M4 17h6l3-9 6 16 3-7h6" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    Pulsebyte
  </a>
  <div class="hdr-right">
    <a class="btn sm" href="../">Trending Projects</a>
    <a class="btn sm" href="../#articles">All Articles</a>
    <a class="btn sm" href="../sponsor.html">Sponsor</a>
    <button class="btn sm" id="theme-btn" onclick="toggleTheme()" aria-label="Toggle theme">🌓</button>
  </div>
</header>

<!-- ══ ARTICLE MAIN WRAP ══ -->
<main class="article-wrap">
  <div class="article-layout">
    <!-- Left / Center Column -->
    <div class="article-main-col">
      <div class="art-back-nav">
        <a class="art-back-btn" href="../#articles">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
          Back to Articles Feed
        </a>
        <span style="font-size:12px;color:var(--ink3)">Technical Deep Dive</span>
      </div>

      <!-- Featured Project Showcase -->
      {project_html}

      <!-- Meta & Title -->
      <div class="art-meta-row">
        <span class="art-badge">Deep Dive</span>
        <span>{read_time}</span>
        <span>&middot;</span>
        <span>{human_date}</span>
      </div>

      <h1 class="reader-title">{esc_title}</h1>
      <div class="reader-tldr">{esc_tldr}</div>
      <div class="reader-tags">{tags_html}</div>

      <!-- Top Social Sharing Bar -->
      <div class="share-bar">
        <span class="share-label">Share:</span>
        <button class="share-btn sb-x" onclick="shareArticle('x')" aria-label="Share on X">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
          X / Twitter
        </button>
        <button class="share-btn sb-linkedin" onclick="shareArticle('linkedin')" aria-label="Share on LinkedIn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
          LinkedIn
        </button>
        <button class="share-btn sb-telegram" onclick="shareArticle('telegram')" aria-label="Share on Telegram">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248-2.04 9.61c-.152.678-.554.843-1.124.524l-3.1-2.284-1.497 1.44c-.165.165-.305.305-.625.305l.223-3.17 5.77-5.213c.25-.224-.055-.348-.39-.124L7.08 14.57l-3.03-.947c-.658-.206-.673-.658.138-.977l11.843-4.566c.548-.199 1.028.134.531.168z"/></svg>
          Telegram
        </button>
        <button class="share-btn sb-reddit" onclick="shareArticle('reddit')" aria-label="Share on Reddit">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.702z"/></svg>
          Reddit
        </button>
        <button class="share-btn sb-facebook" onclick="shareArticle('facebook')" aria-label="Share on Facebook">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
          Facebook
        </button>
        <button class="share-btn sb-copy" onclick="copyArticleLink()">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
          Copy Link
        </button>
      </div>

      <!-- Sponsor Slot: Top -->
      <div id="sponsor-slot-top"></div>

      <!-- Article HTML Content (Semantic <article> for Medium and SEO) -->
      <article class="reader-content" id="r-content">
        {content}
      </article>

      <!-- Sponsor Slot: Bottom -->
      <div id="sponsor-slot-bottom"></div>

      <!-- Bottom Share Bar -->
      <div class="share-bar" style="margin-top:40px">
        <span class="share-label">Enjoyed this breakdown? Share with other developers:</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="share-btn sb-x" onclick="shareArticle('x')">X / Twitter</button>
          <button class="share-btn sb-linkedin" onclick="shareArticle('linkedin')">LinkedIn</button>
          <button class="share-btn sb-telegram" onclick="shareArticle('telegram')">Telegram</button>
          <button class="share-btn sb-reddit" onclick="shareArticle('reddit')">Reddit</button>
          <button class="share-btn sb-facebook" onclick="shareArticle('facebook')">Facebook</button>
          <button class="share-btn sb-copy" onclick="copyArticleLink()">📋 Copy Link</button>
        </div>
      </div>

      <!-- More Articles Section -->
      <section class="more-sec">
        <h3 class="more-title">More Breakdowns from Pulsebyte</h3>
        <div class="more-grid">
          {more_html}
        </div>
      </section>
    </div>

    <!-- ── ARTICLE SIDEBAR ── -->
    <aside class="article-sidebar-col">
      <div id="sponsor-slot-sidebar"></div>

      {sidebar_project_html}

      <div class="sidebar-box">
        <div class="sidebar-box-title">About Pulsebyte</div>
        <div style="font-size:12.5px;color:var(--ink2);line-height:1.5">
          Pulsebyte tracks breakthrough open-source projects across GitHub, Hacker News, Hugging Face, Dev.to and npm, publishing in-depth architectural breakdowns for developers.
        </div>
      </div>

      <div class="sidebar-box" style="background:linear-gradient(135deg,rgba(42,171,238,.07),var(--panel));border-color:color-mix(in srgb,#2AABEE 30%,var(--line))">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <span style="font-size:18px">📢</span>
          <strong style="font-size:13.5px;color:var(--ink)">Developer Community</strong>
        </div>
        <p style="font-size:12px;color:var(--ink2);line-height:1.45;margin-bottom:12px">
          Zero-noise daily alerts on breakthrough GitHub repositories, LLMs, and open source tools.
        </p>
        <a class="btn sm" href="https://t.me/techinfosec" target="_blank" rel="noopener noreferrer" style="background:#2AABEE;color:#fff;border-color:#2AABEE;font-weight:600;width:100%;justify-content:center">
          Join 5,000+ Builders &rarr;
        </a>
      </div>

      <div style="text-align:center;padding:4px">
        <a href="../sponsor.html" style="font-size:11.5px;color:var(--ink3);text-decoration:none">
          Want to feature your product? <strong style="color:var(--acc)">Sponsor Pulsebyte &rarr;</strong>
        </a>
      </div>
    </aside>
  </div>
</main>

<!-- ══ FOOTER ══ -->
<footer>
  <div class="footer-links">
    <a href="../">Home</a>
    <span>&middot;</span>
    <a href="../#articles">Articles</a>
    <span>&middot;</span>
    <a href="../feed.xml" target="_blank">RSS Feed</a>
    <span>&middot;</span>
    <a href="../privacy.html">Privacy Policy</a>
    <span>&middot;</span>
    <a href="../terms.html">Terms of Service</a>
    <span>&middot;</span>
    <a href="../disclaimer.html">Disclaimer</a>
    <span>&middot;</span>
    <a href="../sponsor.html">Advertise / Sponsor</a>
  </div>
  <div>&copy; 2026 Pulsebyte &middot; Auto-scanned &amp; published via GitHub Actions</div>
</footer>

<div id="toast" role="status" aria-live="polite"></div>

<script src="../config.js"></script>
<script>
const CFG = window.PULSEBYTE || {{}};
const ARTICLE_URL = "{canonical_url}";
const ARTICLE_TITLE = {json_title};

function toggleTheme(){{
  var cur = document.documentElement.dataset.theme;
  var next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try {{ localStorage.setItem('pb-theme', next); }} catch(e){{}}
}}

function toast(msg){{
  var el = document.getElementById('toast');
  if(!el) return;
  el.textContent = msg;
  el.style.transform = 'translateX(-50%) translateY(0)';
  setTimeout(function(){{
    el.style.transform = 'translateX(-50%) translateY(100px)';
  }}, 2400);
}}

function copyArticleLink(){{
  if(navigator.clipboard && navigator.clipboard.writeText){{
    navigator.clipboard.writeText(ARTICLE_URL).then(function(){{
      toast('✓ Link copied to clipboard!');
    }}).catch(function(){{
      toast('Could not copy link');
    }});
  }} else {{
    toast('✓ Link copied: ' + ARTICLE_URL);
  }}
}}

function shareArticle(net){{
  var u = encodeURIComponent(ARTICLE_URL);
  var t = encodeURIComponent(ARTICLE_TITLE);
  var map = {{
    x: 'https://twitter.com/intent/tweet?text=' + t + '&url=' + u + '&via=Pulsebyte',
    linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=' + u,
    telegram: 'https://t.me/share/url?url=' + u + '&text=' + t,
    reddit: 'https://reddit.com/submit?url=' + u + '&title=' + t,
    facebook: 'https://www.facebook.com/sharer/sharer.php?u=' + u
  }};
  var target = map[net];
  if(target){{
    window.open(target, '_blank', 'width=600,height=500,noopener,noreferrer');
  }}
}}

// Dynamic sponsors from config.js
(function(){{
  var sponsors = Array.isArray(CFG.sponsors) && CFG.sponsors.length ? CFG.sponsors : (CFG.sponsor && CFG.sponsor.enabled ? [CFG.sponsor] : []);
  function getSponsor(slot){{
    return sponsors.find(function(s){{ return s.enabled && (!s.slots || s.slots[slot] !== false); }});
  }}
  var topSp = getSponsor('article_top');
  if(topSp){{
    var el = document.getElementById('sponsor-slot-top');
    if(el) el.innerHTML = topSp.custom_code || '<div style="background:linear-gradient(135deg,color-mix(in srgb,var(--acc) 10%,var(--panel)),var(--panel));border:1px solid color-mix(in srgb,var(--acc) 30%,var(--line));border-radius:var(--r);padding:14px 18px;margin:20px 0;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap"><div><strong style="font-size:13.5px;color:var(--ink)">' + (topSp.title||'') + '</strong><span style="font-size:13px;color:var(--ink2);margin-left:8px">' + (topSp.desc||'') + '</span></div><a class="btn p sm" href="' + (topSp.url||'#') + '" target="_blank" rel="noopener noreferrer nofollow">' + (topSp.cta||'Learn More →') + '</a></div>';
  }}
  var botSp = getSponsor('article_bottom');
  if(botSp){{
    var el = document.getElementById('sponsor-slot-bottom');
    if(el) el.innerHTML = botSp.custom_code || '<div style="background:linear-gradient(135deg,color-mix(in srgb,var(--acc) 10%,var(--panel)),var(--panel));border:1px solid color-mix(in srgb,var(--acc) 30%,var(--line));border-radius:var(--r);padding:14px 18px;margin:24px 0;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap"><div><strong style="font-size:13.5px;color:var(--ink)">' + (botSp.title||'') + '</strong><span style="font-size:13px;color:var(--ink2);margin-left:8px">' + (botSp.desc||'') + '</span></div><a class="btn p sm" href="' + (botSp.url||'#') + '" target="_blank" rel="noopener noreferrer nofollow">' + (botSp.cta||'Learn More →') + '</a></div>';
  }}
  var sbSp = getSponsor('sidebar');
  if(sbSp){{
    var el = document.getElementById('sponsor-slot-sidebar');
    if(el) el.innerHTML = sbSp.custom_code || '<div class="sidebar-box" style="background:linear-gradient(135deg,color-mix(in srgb,var(--acc) 10%,var(--panel)),var(--panel));border:1px solid color-mix(in srgb,var(--acc) 30%,var(--line))"><span style="font-size:10px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;background:var(--acc-soft);color:var(--acc);padding:2px 6px;border-radius:4px;display:inline-block;margin-bottom:6px">' + (sbSp.badge||'Sponsor') + '</span><div style="font-size:13.5px;font-weight:700;color:var(--ink);margin-bottom:4px">' + (sbSp.title||'') + '</div><p style="font-size:12px;color:var(--ink2);line-height:1.45;margin-bottom:12px">' + (sbSp.desc||'') + '</p><a class="btn p sm" href="' + (sbSp.url||'#') + '" target="_blank" rel="noopener noreferrer nofollow" style="width:100%;justify-content:center">' + (sbSp.cta||'Learn More →') + '</a></div>';
  }}
}})();
</script>
</body>
</html>
"""
    return page_html

def build_all(site_url=SITE_URL):
    if not ARTICLES_FILE.exists():
        print(f"Warning: {ARTICLES_FILE} does not exist.")
        return 0

    try:
        articles = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read articles: {e}")
        return 0

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    styles = extract_styles()

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    published = []
    for a in articles:
        status = a.get("status")
        if status == "draft":
            continue
        if status == "scheduled":
            sched = a.get("scheduled_for", 0)
            if sched and sched > now_ms:
                continue
        published.append(a)

    count = 0
    for art in published:
        slug = art.get("slug") or art.get("id")
        if not slug:
            continue

        # 1. Generate dedicated 1200x630 social preview card for this article
        card_file = CARDS_DIR / f"{slug}.png"
        try:
            generate_social_card(art, card_file)
        except Exception as ce:
            print(f"Warning: could not generate card for {slug}: {ce}")

        # 2. Generate static HTML article page
        html_content = generate_article_page(art, published, styles=styles)
        out_file = ARTICLES_DIR / f"{slug}.html"
        out_file.write_text(html_content, encoding="utf-8")
        count += 1

    # 3. Generate articles/index.html redirect
    index_redirect = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=../#articles">
<title>Pulsebyte Articles</title>
</head>
<body>
<p>Redirecting to <a href="../#articles">Pulsebyte Articles Feed</a>...</p>
</body>
</html>"""
    (ARTICLES_DIR / "index.html").write_text(index_redirect, encoding="utf-8")

    print(f"Generated {count} static article pages and social cards in docs/articles/ and docs/assets/cards/.")
    return count

if __name__ == "__main__":
    build_all()
