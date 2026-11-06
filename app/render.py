import os, asyncio, subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts, imageio_ffmpeg
from mutagen.mp3 import MP3

FD = "C:/Windows/Fonts/"

# Slide themes: (bg_top, bg_bottom, accent, text_primary, text_secondary)
THEMES = [
    ((8,  12, 32),  (20, 80, 120),   (0,  210, 190),  (255,255,255), (180,230,230)),   # teal ocean
    ((25, 10, 45),  (100, 30,  80),  (255,100,160),   (255,255,255), (255,200,220)),   # purple-pink
    ((10, 25, 10),  (20,  90,  40),  (80, 220, 120),  (255,255,255), (200,255,200)),   # emerald
    ((40, 20, 10),  (140, 60,  10),  (255,180, 50),   (255,255,255), (255,230,180)),   # amber fire
    ((10, 10, 40),  (40,  10, 100),  (120,100,255),   (255,255,255), (220,210,255)),   # indigo
    ((30,  5,  5),  (120, 20,  20),  (255, 80, 80),   (255,255,255), (255,200,200)),   # red hot
]

def font(sz, bold=True):
    names = ("segoeuib.ttf" if bold else "segoeui.ttf"), "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"
    for n in names:
        for path in (FD + n, n):
            try: return ImageFont.truetype(path, sz)
            except OSError: pass
    return ImageFont.load_default()

def lerp(a, b, t): return tuple(int(a[i] + (b[i]-a[i]) * t) for i in range(3))

def gradient_bg(w, h, top, bot):
    im = Image.new("RGB", (w, h))
    d  = ImageDraw.Draw(im)
    for y in range(h):
        d.line([(0,y),(w,y)], fill=lerp(top, bot, y/h))
    return im

def noise_overlay(im, alpha=18):
    """Add a subtle grain texture for visual depth."""
    import random
    px = im.load()
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            g = random.randint(-alpha, alpha)
            r,gr,b = px[x,y]
            px[x,y] = (max(0,min(255,r+g)), max(0,min(255,gr+g)), max(0,min(255,b+g)))
    return im

def wrap(draw, text, f, maxw):
    lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def draw_text_shadow(draw, pos, text, font, fill, shadow=(0,0,0,120), offset=4):
    draw.text((pos[0]+offset, pos[1]+offset), text, font=font, fill=shadow)
    draw.text(pos, text, font=font, fill=fill)

def centered_text(draw, text, f, y, W, fill, shadow=True):
    x = (W - draw.textlength(text, font=f)) / 2
    if shadow:
        draw.text((x+3, y+3), text, font=f, fill=(0,0,0,140))
    draw.text((x, y), text, font=f, fill=fill)
    return y + int(f.size * 1.3)

def para_centered(draw, text, f, y, W, fill, maxw, gap=1.3):
    for line in wrap(draw, text, f, maxw):
        y = centered_text(draw, line, f, y, W, fill)
    return y

# ── Card (1080×1080) ──────────────────────────────────────────────────────────
def card(dr, path):
    it    = dr["item"]
    idx   = hash(it["name"]) % len(THEMES)
    top, bot, acc, txt1, txt2 = THEMES[idx]
    W, H  = 1080, 1080
    im    = gradient_bg(W, H, top, bot)
    im    = noise_overlay(im)
    d     = ImageDraw.Draw(im, "RGBA")

    # Decorative circles (depth)
    for cx,cy,cr,ca in [(900,150,280,25),(200,900,200,20),(600,600,350,12)]:
        overlay = Image.new("RGBA",(W,H),(0,0,0,0))
        od = ImageDraw.Draw(overlay)
        od.ellipse((cx-cr,cy-cr,cx+cr,cy+cr), fill=(*acc, ca))
        im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)

    # Source badge
    src_txt = it["src"]
    sf = font(32); sw = int(d.textlength(src_txt, font=sf))
    d.rounded_rectangle((60,60,60+sw+40,116), 28, fill=(*acc,220))
    d.text((80,68), src_txt, font=sf, fill=(20,20,30))

    # Stars badge
    score_txt = f"★ {it.get('score',0)}"
    stf = font(32, False); stw = int(d.textlength(score_txt, font=stf))
    d.rounded_rectangle((W-stw-56,60,W-60,116), 28, fill=(255,255,255,30))
    d.text((W-stw-36,68), score_txt, font=stf, fill=(255,215,100))

    # Hook
    hook = dr.get("hook","")
    hf = font(76); y = 160
    for line in wrap(d, hook, hf, 940):
        draw_text_shadow(d,(70,y),line,hf,(255,255,255),(0,0,0))
        y += int(hf.size*1.12)

    # Accent line under hook
    y += 12
    d.rectangle((70,y,70+300,y+5), fill=(*acc,255))
    y += 24

    # Card title
    ctf = font(46, False)
    ct  = dr.get("card_title", it["name"])
    for line in wrap(d, ct, ctf, 940):
        draw_text_shadow(d,(70,y),line,ctf,txt2,(0,0,0))
        y += int(ctf.size*1.2)
    y += 18

    # Bullet points
    bf = font(40, False)
    for pt in dr.get("card_points",[])[:3]:
        # bullet circle
        d.ellipse((70,y+14,96,y+40), fill=(*acc,255))
        d.ellipse((76,y+20,90,y+34), fill=(255,255,255))
        blines = wrap(d, pt, bf, 870)
        for li,bl in enumerate(blines):
            draw_text_shadow(d,(116 if li==0 else 116, y),bl,bf,(255,255,255),(0,0,0,120),3)
            y += int(bf.size*1.22)
        y += 8

    # Bottom bar
    d.rectangle((0, H-110, W, H), fill=(0,0,0,120))
    nf  = font(38); nm = it["name"]
    d.text((70, H-90), nm, font=nf, fill=(255,255,255))
    lang = it.get("lang","")
    meta_parts = [f"★ {it.get('score','')}"]
    if lang: meta_parts.append(lang)
    mf   = font(30, False)
    meta = "  •  ".join(meta_parts)
    d.text((70, H-46), meta, font=mf, fill=(255,215,100))

    im.save(path, quality=95); return path


# ── Video slide (1080×1920) ───────────────────────────────────────────────────
def slide(text, caption, emoji, idx, dr, path):
    it          = dr["item"]
    tidx        = idx % len(THEMES)
    top, bot, acc, txt1, txt2 = THEMES[tidx]
    W, H        = 1080, 1920
    im          = gradient_bg(W, H, top, bot)
    im          = noise_overlay(im, 12)
    d           = ImageDraw.Draw(im, "RGBA")

    # Background decorative shapes
    overlay = Image.new("RGBA",(W,H),(0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((-100,-100,500,500), fill=(*acc,18))
    od.ellipse((600,1400,1200,2050), fill=(*acc,15))
    od.ellipse((800,300,1200,700), fill=(255,255,255,8))
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(im)

    # Slide number dots at top
    dot_y = 60
    total = 6
    dot_spacing = 24
    dot_start   = (W - (total*14 + (total-1)*dot_spacing)) // 2
    for di in range(total):
        cx = dot_start + di*(14+dot_spacing)
        filled = di == idx
        col = (*acc,255) if filled else (255,255,255,80)
        if filled:
            d.ellipse((cx-7,dot_y-7,cx+7,dot_y+7), fill=col)
        else:
            d.ellipse((cx-5,dot_y-5,cx+5,dot_y+5), fill=col)

    # Project name pill at top
    nf  = font(34); nm = it["name"]
    nw  = int(d.textlength(nm, font=nf))
    nx  = (W-nw-40)//2
    d.rounded_rectangle((nx,100,nx+nw+40,152), 26, fill=(255,255,255,25))
    d.text((nx+20,108), nm, font=nf, fill=(255,255,255))

    # Big emoji (centered upper third)
    ef = font(180)
    try:
        # Try drawing emoji — may not render on all systems, fallback gracefully
        ew = int(d.textlength(emoji, font=ef))
        d.text(((W-ew)//2, 220), emoji, font=ef, fill=(255,255,255))
    except Exception:
        pass

    # Short caption (slide_text) — large, center
    cf_size = 100 if len(caption) < 20 else 80 if len(caption) < 35 else 68
    cf = font(cf_size)
    cap_y = 500
    for line in wrap(d, caption, cf, 920):
        lw = d.textlength(line, font=cf)
        # Shadow
        d.text(((W-lw)//2+4, cap_y+4), line, font=cf, fill=(0,0,0,160))
        d.text(((W-lw)//2,   cap_y),   line, font=cf, fill=(255,255,255))
        cap_y += int(cf.size*1.18)

    # Accent divider
    cap_y += 24
    bar_w = 160
    d.rounded_rectangle(((W-bar_w)//2, cap_y, (W+bar_w)//2, cap_y+6), 3, fill=(*acc,255))
    cap_y += 36

    # Narration text (smaller, readable)
    nrf_size = 52 if len(text) < 60 else 44 if len(text) < 100 else 38
    nrf = font(nrf_size, False)
    nr_y = cap_y + 10
    for line in wrap(d, text, nrf, 880):
        lw = d.textlength(line, font=nrf)
        d.text(((W-lw)//2, nr_y), line, font=nrf, fill=(*txt2,230))
        nr_y += int(nrf.size*1.3)

    # Bottom branding bar
    bar_h = 160
    bar_overlay = Image.new("RGBA",(W,H),(0,0,0,0))
    bd = ImageDraw.Draw(bar_overlay)
    bd.rectangle((0,H-bar_h,W,H), fill=(0,0,0,180))
    im = Image.alpha_composite(im.convert("RGBA"), bar_overlay).convert("RGB")
    d  = ImageDraw.Draw(im)

    # Brand name
    brnd = font(48); bname = "Pulsebyte"
    bw   = int(d.textlength(bname, font=brnd))
    d.text(((W-bw)//2, H-bar_h+28), bname, font=brnd, fill=(*acc,255))

    # Score & source
    sf_b = font(34, False); smeta = f"★ {it.get('score','')}  |  {it['src']}"
    sw_b = int(d.textlength(smeta, font=sf_b))
    d.text(((W-sw_b)//2, H-bar_h+90), smeta, font=sf_b, fill=(255,255,255))

    im.save(path, quality=95)


# ── Video assembly ────────────────────────────────────────────────────────────
def video(dr, outdir):
    ff     = imageio_ffmpeg.get_ffmpeg_exe()
    voice  = os.getenv("EDGE_VOICE", "en-US-AndrewNeural")
    script = dr.get("script", [])
    texts  = dr.get("slide_texts", [""] * len(script))
    emojis = dr.get("slide_emojis", ["🔥"] * len(script))
    segs   = []

    # Pad lists to match script length
    while len(texts)  < len(script): texts.append("")
    while len(emojis) < len(script): emojis.append("🔥")

    for i, line in enumerate(script):
        png  = os.path.join(outdir, f"s{i}.png")
        mp3  = os.path.join(outdir, f"s{i}.mp3")
        seg  = os.path.join(outdir, f"s{i}.mp4")

        slide(line, texts[i], emojis[i], i, dr, png)
        asyncio.run(edge_tts.Communicate(line, voice).save(mp3))

        dur    = MP3(mp3).info.length + 0.5
        frames = int(dur * 30)

        # Alternate zoom direction per slide for visual variety
        if i % 2 == 0:
            zoom_expr = f"min(zoom+0.0004,1.06)"
            x_expr    = "iw/2-(iw/zoom/2)"
            y_expr    = "ih/2-(ih/zoom/2)"
        else:
            zoom_expr = f"max(1.06-on*0.0004,1.0)"
            x_expr    = "iw/2-(iw/zoom/2)"
            y_expr    = "ih/2-(ih/zoom/2)"

        vf = (
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={frames}:s=1080x1920:fps=30,"
            f"fade=t=in:st=0:d=0.25,"
            f"fade=t=out:st={max(0,dur-0.3):.2f}:d=0.25,"
            f"format=yuv420p"
        )
        subprocess.run([
            ff, "-y", "-loglevel", "error",
            "-loop", "1", "-i", png,
            "-i", mp3,
            "-vf", vf,
            "-af", "apad,afade=t=in:st=0:d=0.1,afade=t=out:st={:.2f}:d=0.2".format(max(0,dur-0.25)),
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            seg
        ], check=True)
        segs.append(f"s{i}.mp4")

    with open(os.path.join(outdir,"list.txt"),"w") as f:
        f.write("\n".join(f"file '{s}'" for s in segs))

    subprocess.run([
        ff, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", "list.txt",
        "-c", "copy", "short.mp4"
    ], cwd=outdir, check=True)

    return os.path.join(outdir, "short.mp4")
