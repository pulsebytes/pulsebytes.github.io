"""Generates complete branding materials for Pulsebyte:
- Favicon (SVG, ICO, PNGs)
- Square Logos (SVG, 512x512 PNG)
- Full Wordmark Logos (SVG, PNG)
- Facebook Cover Banner (1640x924 PNG)
- Twitter / X Banner (1500x500 PNG)
- OpenGraph & Telegram Social Preview (1200x630 PNG)
"""
import os, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

FONTS_DIR = "C:/Windows/Fonts/"

def get_font(size, bold=True):
    candidates = (
        ["segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf", "calibrib.ttf"]
    )
    for name in candidates:
        p = Path(FONTS_DIR) / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_pulse_mark(draw, cx, cy, radius, stroke_width=8, color=(255, 255, 255)):
    """Draws the signature Pulsebyte heartbeat ECG wave: flat - down - high peak - deep drop - rebound - flat."""
    scale = radius / 40.0
    # Base baseline
    y0 = cy
    pts = [
        (cx - 36 * scale, y0),
        (cx - 20 * scale, y0),
        (cx - 12 * scale, y0 + 10 * scale),
        (cx - 3  * scale, y0 - 32 * scale),
        (cx + 8  * scale, y0 + 26 * scale),
        (cx + 17 * scale, y0 - 12 * scale),
        (cx + 24 * scale, y0),
        (cx + 36 * scale, y0)
    ]
    # Draw thick polyline with rounded joins
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=color, width=int(stroke_width))
        draw.ellipse([pts[i][0] - stroke_width/2, pts[i][1] - stroke_width/2,
                      pts[i][0] + stroke_width/2, pts[i][1] + stroke_width/2], fill=color)
    draw.ellipse([pts[-1][0] - stroke_width/2, pts[-1][1] - stroke_width/2,
                  pts[-1][0] + stroke_width/2, pts[-1][1] + stroke_width/2], fill=color)

def generate_svg_logo(output_path, size=512):
    """Clean vector SVG logo."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="45%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
  <!-- Background Shield -->
  <rect x="32" y="32" width="{size - 64}" height="{size - 64}" rx="{int(size * 0.22)}" fill="url(#bg)" filter="url(#shadow)"/>
  <rect x="32" y="32" width="{size - 64}" height="{size - 64}" rx="{int(size * 0.22)}" fill="url(#glow)"/>
  
  <!-- Subtle border highlight -->
  <rect x="33" y="33" width="{size - 66}" height="{size - 66}" rx="{int(size * 0.22)}" fill="none" stroke="#ffffff" stroke-opacity="0.2" stroke-width="2"/>
  
  <!-- Signature Pulse Wave -->
  <path d="M 96,256 L 160,256 L 192,296 L 232,128 L 280,368 L 320,216 L 352,256 L 416,256"
        fill="none"
        stroke="#ffffff"
        stroke-width="32"
        stroke-linecap="round"
        stroke-linejoin="round"/>
</svg>"""
    output_path.write_text(svg, encoding="utf-8")

def generate_svg_logo_full(output_path):
    """Full horizontal logo SVG."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" width="800" height="200">
  <defs>
    <linearGradient id="markBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="45%" stop-color="#2563eb"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
    <linearGradient id="textGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <!-- Icon Mark -->
  <g transform="translate(30, 30)">
    <rect width="140" height="140" rx="32" fill="url(#markBg)"/>
    <path d="M 24,70 L 44,70 L 54,82 L 67,36 L 81,104 L 94,58 L 104,70 L 120,70"
          fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
  <!-- Typography -->
  <text x="195" y="112" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="64" font-weight="800" fill="#0f172a" letter-spacing="-1.5">Pulse<tspan fill="#2563eb">byte</tspan></text>
  <text x="198" y="148" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-size="16" font-weight="600" fill="#64748b" letter-spacing="2.5">OPEN-SOURCE INTELLIGENCE &amp; CODE ARCHITECTURE</text>
</svg>"""
    output_path.write_text(svg, encoding="utf-8")

def generate_png_logo(output_path, size=512):
    """Generate high-resolution square logo PNG."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    pad = int(size * 0.08)
    corner = int(size * 0.22)
    # Background gradient
    grad = Image.new("RGB", (size - 2 * pad, size - 2 * pad))
    gd = ImageDraw.Draw(grad)
    c1, c2 = (2, 132, 199), (124, 58, 237)
    for y in range(grad.height):
        t = y / grad.height
        col = (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t)
        )
        gd.line([(0, y), (grad.width, y)], fill=col)

    # Rounded mask
    mask = Image.new("L", (grad.width, grad.height), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, grad.width, grad.height], radius=corner, fill=255)

    # Paste gradient with mask
    im.paste(grad, (pad, pad), mask)

    # Draw pulse line
    cx, cy = size // 2, size // 2
    r = int(size * 0.38)
    draw_pulse_mark(d, cx, cy, r, stroke_width=int(size * 0.065), color=(255, 255, 255, 255))

    im.save(output_path, "PNG")
    return im

def generate_favicons():
    """Generates favicon.svg, favicon-16x16, favicon-32x32, apple-touch-icon, and favicon.ico."""
    generate_svg_logo(DOCS / "favicon.svg", size=128)
    
    # 512x512 master
    master = generate_png_logo(ASSETS / "logo.png", size=512)
    
    # Apple touch icon (180x180)
    touch = master.resize((180, 180), Image.Resampling.LANCZOS)
    touch.save(DOCS / "apple-touch-icon.png", "PNG")
    touch.save(ASSETS / "apple-touch-icon.png", "PNG")

    # 32x32 & 16x16 PNGs
    f32 = master.resize((32, 32), Image.Resampling.LANCZOS)
    f16 = master.resize((16, 16), Image.Resampling.LANCZOS)
    f48 = master.resize((48, 48), Image.Resampling.LANCZOS)

    f32.save(DOCS / "favicon-32x32.png", "PNG")
    f16.save(DOCS / "favicon-16x16.png", "PNG")

    # Multi-size ICO
    master.save(DOCS / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("Favicons generated successfully.")

def generate_social_banners():
    """Generates Facebook banner, Twitter banner, and OpenGraph/Telegram cover."""
    # 1. FACEBOOK COVER BANNER (1640 x 924)
    fb_w, fb_h = 1640, 924
    fb = Image.new("RGB", (fb_w, fb_h), (11, 15, 25))
    fbd = ImageDraw.Draw(fb)

    # Gradient background lighting
    for y in range(fb_h):
        t = y / fb_h
        r = int(9 + 12 * math.sin(t * math.pi))
        g = int(14 + 20 * math.sin(t * math.pi))
        b = int(28 + 48 * math.sin(t * math.pi))
        fbd.line([(0, y), (fb_w, y)], fill=(r, g, b))

    # Tech grid pattern overlay
    grid_col = (25, 35, 60)
    for x in range(0, fb_w, 40):
        fbd.line([(x, 0), (x, fb_h)], fill=grid_col, width=1)
    for y in range(0, fb_h, 40):
        fbd.line([(0, y), (fb_w, y)], fill=grid_col, width=1)

    # Soft glowing radial aura behind logo
    aura = Image.new("RGBA", (fb_w, fb_h), (0, 0, 0, 0))
    ad = ImageDraw.Draw(aura)
    ad.ellipse([150, 150, 750, 750], fill=(37, 99, 235, 45))
    ad.ellipse([950, 100, 1550, 700], fill=(99, 102, 241, 35))
    aura = aura.filter(ImageFilter.GaussianBlur(60))
    fb.paste(aura, (0, 0), aura)
    fbd = ImageDraw.Draw(fb)

    # Draw Badge Icon on Left (Center area safe for mobile)
    icon_sz = 140
    icon_x, icon_y = 120, 260
    icon_bg = Image.new("RGB", (icon_sz, icon_sz))
    ibd = ImageDraw.Draw(icon_bg)
    for y in range(icon_sz):
        t = y / icon_sz
        ibd.line([(0, y), (icon_sz, y)], fill=(int(2 + 122*t), int(132 - 74*t), int(199 + 38*t)))
    imask = Image.new("L", (icon_sz, icon_sz), 0)
    ImageDraw.Draw(imask).rounded_rectangle([0, 0, icon_sz, icon_sz], radius=32, fill=255)
    fb.paste(icon_bg, (icon_x, icon_y), imask)
    draw_pulse_mark(fbd, icon_x + icon_sz // 2, icon_y + icon_sz // 2, 54, stroke_width=10, color=(255, 255, 255))

    # Main Typography
    font_brand = get_font(72, bold=True)
    font_sub = get_font(34, bold=True)
    font_tag = get_font(22, bold=False)
    font_chip = get_font(18, bold=True)

    fbd.text((icon_x + icon_sz + 36, icon_y + 10), "Pulsebyte", font=font_brand, fill=(255, 255, 255))
    fbd.text((icon_x + icon_sz + 380, icon_y + 45), "AI & OPEN-SOURCE", font=font_chip, fill=(56, 189, 248))

    fbd.text((icon_x, icon_y + 180), "What developers are shipping right now.", font=font_sub, fill=(241, 245, 249))
    fbd.text((icon_x, icon_y + 235), "Automated 24/7 scanning across GitHub, GitLab, Hugging Face, Codeberg & Product Hunt.", font=font_tag, fill=(148, 163, 184))

    # Source Chips Pill Bar
    chips_y = icon_y + 310
    chips = ["⭐ GitHub Trending", "🦊 GitLab", "🤗 Hugging Face", "🏔️ Codeberg", "🚀 Product Hunt", "📰 Technical Articles"]
    cx_offset = icon_x
    for ch in chips:
        fbd.rounded_rectangle([cx_offset, chips_y, cx_offset + 190, chips_y + 44], radius=22, fill=(30, 41, 59), outline=(51, 65, 85), width=1)
        fbd.text((cx_offset + 16, chips_y + 11), ch, font=font_chip, fill=(226, 232, 240))
        cx_offset += 205

    # Bottom Footer on Cover
    fbd.text((icon_x, fb_h - 100), "🌐 pulsebytes.github.io  ·  📢 t.me/techinfosec  ·  📘 facebook.com/z3dd3v", font=font_chip, fill=(100, 116, 139))
    fb.save(ASSETS / "facebook-banner.png", "PNG")

    # 2. TWITTER / X HEADER BANNER (1500 x 500)
    tw_w, tw_h = 1500, 500
    tw = Image.new("RGB", (tw_w, tw_h), (10, 14, 26))
    twd = ImageDraw.Draw(tw)

    for y in range(tw_h):
        t = y / tw_h
        twd.line([(0, y), (tw_w, y)], fill=(int(8 + 8*t), int(12 + 16*t), int(26 + 32*t)))

    # Grid
    for x in range(0, tw_w, 36): twd.line([(x, 0), (x, tw_h)], fill=(22, 32, 54), width=1)
    for y in range(0, tw_h, 36): twd.line([(0, y), (tw_w, y)], fill=(22, 32, 54), width=1)

    # Center Logo Mark
    tcx, tcy = 220, 250
    t_icon_sz = 110
    t_icon = Image.new("RGB", (t_icon_sz, t_icon_sz), (37, 99, 235))
    t_mask = Image.new("L", (t_icon_sz, t_icon_sz), 0)
    ImageDraw.Draw(t_mask).rounded_rectangle([0, 0, t_icon_sz, t_icon_sz], radius=26, fill=255)
    tw.paste(t_icon, (tcx - t_icon_sz // 2, tcy - t_icon_sz // 2), t_mask)
    draw_pulse_mark(twd, tcx, tcy, 42, stroke_width=8, color=(255, 255, 255))

    font_tw_brand = get_font(60, bold=True)
    font_tw_sub = get_font(26, bold=True)
    font_tw_desc = get_font(18, bold=False)

    twd.text((tcx + 85, tcy - 52), "Pulsebyte", font=font_tw_brand, fill=(255, 255, 255))
    twd.text((tcx + 88, tcy + 18), "Open-Source Intelligence & Architecture Breakdowns", font=font_tw_sub, fill=(56, 189, 248))
    twd.text((tcx + 88, tcy + 56), "Curated breakthroughs across AI models, developer tools, and scalable systems.", font=font_tw_desc, fill=(148, 163, 184))

    # URL callout
    twd.text((tw_w - 320, tw_h - 50), "pulsebytes.github.io", font=get_font(20, bold=True), fill=(100, 116, 139))
    tw.save(ASSETS / "twitter-banner.png", "PNG")

    # 3. OPENGRAPH / TELEGRAM SOCIAL PREVIEW (1200 x 630)
    og_w, og_h = 1200, 630
    og = Image.new("RGB", (og_w, og_h), (11, 15, 25))
    ogd = ImageDraw.Draw(og)

    for y in range(og_h):
        t = y / og_h
        ogd.line([(0, y), (og_w, y)], fill=(int(10 + 10*t), int(15 + 20*t), int(28 + 40*t)))

    for x in range(0, og_w, 40): ogd.line([(x, 0), (x, og_h)], fill=(24, 34, 58), width=1)
    for y in range(0, og_h, 40): ogd.line([(0, y), (og_w, y)], fill=(24, 34, 58), width=1)

    # Logo Mark
    mcx, mcy = 600, 200
    m_sz = 130
    m_im = Image.new("RGB", (m_sz, m_sz), (37, 99, 235))
    m_mask = Image.new("L", (m_sz, m_sz), 0)
    ImageDraw.Draw(m_mask).rounded_rectangle([0, 0, m_sz, m_sz], radius=32, fill=255)
    og.paste(m_im, (mcx - m_sz // 2, mcy - m_sz // 2), m_mask)
    draw_pulse_mark(ogd, mcx, mcy, 48, stroke_width=9, color=(255, 255, 255))

    ogd.text((600 - 150, 290), "Pulsebyte", font=get_font(64, bold=True), fill=(255, 255, 255))
    
    sub_text = "What developers are shipping right now"
    f_sub = get_font(30, bold=True)
    w_sub = ogd.textlength(sub_text, font=f_sub)
    ogd.text((600 - w_sub // 2, 375), sub_text, font=f_sub, fill=(56, 189, 248))

    desc_text = "Real-time discovery & in-depth AI breakdowns of breakthrough open-source projects."
    f_desc = get_font(20, bold=False)
    w_desc = ogd.textlength(desc_text, font=f_desc)
    ogd.text((600 - w_desc // 2, 425), desc_text, font=f_desc, fill=(148, 163, 184))

    # Badge chips
    ogd.rounded_rectangle([440, 480, 760, 526], radius=23, fill=(30, 41, 59), outline=(56, 189, 248), width=1)
    ogd.text((475, 492), "🌐 pulsebytes.github.io", font=get_font(20, bold=True), fill=(255, 255, 255))

    og.save(ASSETS / "og-image.png", "PNG")
    og.save(DOCS / "og-image.png", "PNG")
    og.save(ASSETS / "telegram-cover.png", "PNG")

    print("Social banners generated successfully.")

def generate_branding_doc():
    """Generates BRANDING.md with full copy kit, bios, color codes, and voice guidelines."""
    doc = """# Pulsebyte — Official Brand Kit & Social Copy Deck

Welcome to the official brand guidelines and copy kit for **Pulsebyte** ([pulsebytes.github.io](https://pulsebytes.github.io/)).

---

## 1. Brand Identity & Taglines

### Primary Tagline
> **"What developers are shipping right now."**

### Alternative Taglines
- **The Developer Radar:** "Real-time discovery and architecture breakdowns of breakthrough open source."
- **For AI Engineers:** "Never miss a breakthrough LLM, agent framework, or developer tool."
- **For Telegram:** "Zero-noise daily drops of breakthrough GitHub repositories."

---

## 2. Social Media Bios (Ready to Copy-Paste)

### 🐦 Twitter / X Bio (155 characters)
```text
What developers are shipping right now. Real-time open-source discovery & AI-powered technical breakdowns. ⚡ Live feed: pulsebytes.github.io
```

### ✈️ Telegram Channel Bio (248 characters)
```text
Daily zero-noise drops of breakthrough open-source projects, AI tools, and system architecture breakdowns. Auto-scanned 24/7 across GitHub, GitLab, and Hugging Face.
🌐 Website: pulsebytes.github.io
💼 Partnerships: zeddev@duck.com
```

### 📘 Facebook Page About / Description
#### Short (150 chars):
```text
Real-time open-source intelligence, trending developer projects, and in-depth AI technical breakdowns.
```
#### Full Description (Page Story):
```text
Pulsebyte is an automated developer intelligence platform that monitors GitHub, GitLab, Hugging Face, Codeberg, and Product Hunt 24 hours a day, 7 days a week.

We cut through developer hype to deliver:
• Real-time discovery of breakthrough open-source repositories.
• In-depth architectural breakdowns and benchmark analyses.
• Zero-noise summaries of new AI models, developer tools, and backend frameworks.

Follow us to stay ahead of the technology curve and discover what the world's best software engineers are building right now.

🌐 Website: https://pulsebytes.github.io/
✈️ Telegram: https://t.me/techinfosec
💼 Sponsorships & Inquiries: zeddev@duck.com
```

### 🐙 GitHub Organization Bio (160 characters)
```text
Real-time open-source intelligence and technical architecture breakdowns. Curated for developers who build. 🌐 pulsebytes.github.io
```

### 💼 LinkedIn Page Summary
```text
Pulsebyte is a real-time developer publication and open-source intelligence feed. We track trending repositories, breakthrough AI research, and scalable infrastructure tools across global developer ecosystems. 

Our mission is to help software engineers, founders, and engineering leaders discover high-impact open-source technology before it becomes mainstream.
```

---

## 3. Brand Assets Directory (`docs/assets/`)

| File | Resolution | Format | Purpose |
|---|---|---|---|
| `docs/favicon.ico` | Multi (16, 32, 48, 64) | ICO | Browser tab icon |
| `docs/favicon.svg` | Scalable Vector | SVG | Modern browsers & PWA |
| `docs/apple-touch-icon.png` | 180 × 180 | PNG | iOS Home Screen icon |
| `docs/assets/logo.png` | 512 × 512 | PNG | Profile picture for X, Telegram, Facebook, GitHub |
| `docs/assets/logo.svg` | Scalable Vector | SVG | High-res vector icon mark |
| `docs/assets/logo-full.svg` | 800 × 200 | SVG | Full horizontal wordmark |
| `docs/assets/facebook-banner.png` | 1640 × 924 | PNG | Facebook Page Cover (mobile-safe center) |
| `docs/assets/twitter-banner.png` | 1500 × 500 | PNG | Twitter / X Profile Header |
| `docs/assets/og-image.png` | 1200 × 630 | PNG | OpenGraph social preview card for link shares |
| `docs/assets/telegram-cover.png` | 1200 × 630 | PNG | Telegram Channel background / pinned image |

---

## 4. Visual Identity & Color Palette

### Primary Colors
- **Pulse Blue (Accent):** `#2563EB` / `rgb(37, 99, 235)`
- **Electric Cyan (Highlight):** `#38BDF8` / `rgb(56, 189, 248)`
- **Deep Slate (Dark Mode Bg):** `#090D16` / `rgb(9, 13, 22)`
- **Panel Surface:** `#0F172A` / `rgb(15, 23, 42)`
- **Light Bg:** `#F8FAFC` / `rgb(248, 250, 252)`
- **Success Green:** `#16A34A` / `rgb(22, 163, 74)`
- **Star Orange / Fire:** `#F59E0B` / `rgb(245, 158, 11)`

### Typography
- **Headings & Display:** `Bricolage Grotesque` (Geometric, punchy, high-character)
- **Body & Prose:** `Plus Jakarta Sans` (Clean modern grotesque, optimized for readability)
- **Code & Metadata:** `JetBrains Mono` (Zero-ambiguity monospace)

---

## 5. Contact & Partnerships
- **Sponsorships & Featured Partners:** `zeddev@duck.com`
- **Official Media Kit:** [pulsebytes.github.io/sponsor.html](https://pulsebytes.github.io/sponsor.html)
"""
    (ASSETS / "BRANDING.md").write_text(doc, encoding="utf-8")
    print("BRANDING.md generated successfully.")

if __name__ == "__main__":
    generate_favicons()
    generate_svg_logo(ASSETS / "logo.svg", size=512)
    generate_svg_logo_full(ASSETS / "logo-full.svg")
    generate_social_banners()
    generate_branding_doc()
    print("All branding materials created successfully!")
