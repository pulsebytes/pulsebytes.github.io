"""Automated RSS 2.0 and Atom 1.0 Feed Generator for Pulsebyte.
Generates docs/feed.xml, docs/rss.xml, and docs/atom.xml from docs/articles.json.
Compatible with Substack, Medium, Ghost, Beehiiv, Feedly, and RSS readers.
"""
import os
import sys
import json
import html
import urllib.parse
from datetime import datetime, timezone
import email.utils
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ARTICLES_FILE = DOCS / "articles.json"

SITE_URL = os.getenv("SITE_URL", "https://pulsebytes.github.io").rstrip("/")
FEED_TITLE = "Pulsebyte · Developer Breakthroughs & Architecture Deep Dives"
FEED_DESC = "In-depth architectural breakdowns, engineering deep-dives, and curated open-source projects for developers."
FEED_AUTHOR = "Pulsebyte Editorial"

def parse_date(val):
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, (int, float)):
        # Milliseconds timestamp if > 1e11
        if val > 1e11:
            val /= 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            f = float(val)
            if f > 1e11:
                f /= 1000.0
            return datetime.fromtimestamp(f, tz=timezone.utc)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)

def sanitize_cdata(text):
    if not text:
        return ""
    # Avoid breaking CDATA closure
    return text.replace("]]>", "]]]]><![CDATA[>")

def generate_rss(articles, site_url=SITE_URL):
    now_rfc = email.utils.format_datetime(datetime.now(timezone.utc))
    
    items_xml = []
    for art in articles:
        # Check if article is published
        status = art.get("status")
        if status == "draft":
            continue
        if status == "scheduled":
            sched_for = art.get("scheduled_for", 0)
            if sched_for and sched_for > int(datetime.now(timezone.utc).timestamp() * 1000):
                continue

        art_id = art.get("id") or ""
        slug = art.get("slug")
        if slug:
            link = f"{site_url}/article.html?slug={urllib.parse.quote(str(slug))}"
        else:
            link = f"{site_url}/article.html?id={urllib.parse.quote(str(art_id))}"

        pub_dt = parse_date(art.get("published_at") or art.get("date") or art.get("created_at"))
        pub_rfc = email.utils.format_datetime(pub_dt)

        title = html.escape(art.get("title") or "Untitled Breakdown")
        excerpt = art.get("tldr") or art.get("excerpt") or ""
        content = art.get("content") or excerpt

        tags = art.get("tags") or []
        cat_xml = "\n".join(f"      <category>{html.escape(str(t))}</category>" for t in tags)

        item = f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{pub_rfc}</pubDate>
      <dc:creator><![CDATA[{FEED_AUTHOR}]]></dc:creator>
{cat_xml}
      <description><![CDATA[{sanitize_cdata(excerpt)}]]></description>
      <content:encoded><![CDATA[{sanitize_cdata(content)}]]></content:encoded>
      <enclosure url="{site_url}/assets/og-image.png" length="0" type="image/png" />
    </item>"""
        items_xml.append(item)

    items_block = "\n".join(items_xml)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:wfw="http://wellformedweb.org/CommentAPI/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(FEED_TITLE)}</title>
    <atom:link href="{site_url}/feed.xml" rel="self" type="application/rss+xml" />
    <link>{site_url}/</link>
    <description>{html.escape(FEED_DESC)}</description>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <language>en-US</language>
    <generator>Pulsebyte RSS Engine 2.0</generator>
    <image>
      <url>{site_url}/assets/logo.png</url>
      <title>{html.escape(FEED_TITLE)}</title>
      <link>{site_url}/</link>
    </image>
{items_block}
  </channel>
</rss>
"""
    return xml

def generate_atom(articles, site_url=SITE_URL):
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    entries_xml = []
    for art in articles:
        status = art.get("status")
        if status == "draft":
            continue
        if status == "scheduled":
            sched_for = art.get("scheduled_for", 0)
            if sched_for and sched_for > int(datetime.now(timezone.utc).timestamp() * 1000):
                continue

        art_id = art.get("id") or ""
        slug = art.get("slug")
        if slug:
            link = f"{site_url}/article.html?slug={urllib.parse.quote(str(slug))}"
        else:
            link = f"{site_url}/article.html?id={urllib.parse.quote(str(art_id))}"

        pub_dt = parse_date(art.get("published_at") or art.get("date") or art.get("created_at"))
        pub_iso = pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        title = html.escape(art.get("title") or "Untitled Breakdown")
        excerpt = art.get("tldr") or art.get("excerpt") or ""
        content = art.get("content") or excerpt

        entry = f"""  <entry>
    <title>{title}</title>
    <link rel="alternate" type="text/html" href="{link}"/>
    <id>{link}</id>
    <updated>{pub_iso}</updated>
    <published>{pub_iso}</published>
    <author>
      <name>{FEED_AUTHOR}</name>
    </author>
    <summary type="html"><![CDATA[{sanitize_cdata(excerpt)}]]></summary>
    <content type="html"><![CDATA[{sanitize_cdata(content)}]]></content>
  </entry>"""
        entries_xml.append(entry)

    entries_block = "\n".join(entries_xml)

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{html.escape(FEED_TITLE)}</title>
  <subtitle>{html.escape(FEED_DESC)}</subtitle>
  <link href="{site_url}/atom.xml" rel="self"/>
  <link href="{site_url}/"/>
  <id>{site_url}/</id>
  <updated>{now_iso}</updated>
{entries_block}
</feed>
"""
    return xml

def build_all(site_url=SITE_URL):
    if not ARTICLES_FILE.exists():
        print(f"Warning: {ARTICLES_FILE} does not exist.")
        return False

    try:
        articles = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read articles: {e}")
        return False

    rss_xml = generate_rss(articles, site_url)
    atom_xml = generate_atom(articles, site_url)

    feed_file = DOCS / "feed.xml"
    rss_file = DOCS / "rss.xml"
    atom_file = DOCS / "atom.xml"

    feed_file.write_text(rss_xml, encoding="utf-8")
    rss_file.write_text(rss_xml, encoding="utf-8")
    atom_file.write_text(atom_xml, encoding="utf-8")

    pub_count = sum(1 for a in articles if a.get("status") not in ("draft", "scheduled"))
    print(f"Generated feeds ({pub_count} published articles):")
    print(f" - {feed_file} ({len(rss_xml.encode('utf-8'))} bytes)")
    print(f" - {rss_file} ({len(rss_xml.encode('utf-8'))} bytes)")
    print(f" - {atom_file} ({len(atom_xml.encode('utf-8'))} bytes)")
    return True

if __name__ == "__main__":
    build_all()
