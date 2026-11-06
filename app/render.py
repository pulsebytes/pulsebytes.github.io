import os, asyncio, subprocess
from PIL import Image, ImageDraw, ImageFont
import edge_tts, imageio_ffmpeg
from mutagen.mp3 import MP3

FD = "C:/Windows/Fonts/"
PALETTES = [((12, 20, 38), (15, 118, 110)), ((28, 18, 46), (190, 80, 60)), ((10, 30, 40), (60, 100, 200)), ((30, 24, 14), (200, 150, 30))]

def font(sz, bold=True):
    for n in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(FD + n, sz)
        except OSError:
            try: return ImageFont.truetype(n, sz)
            except OSError: pass
    return ImageFont.load_default()

def bg(w, h, pal):
    c1, c2 = pal; im = Image.new("RGB", (w, h)); d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h * 0.85
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return im

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + ([cur] if cur else [])

def para(d, text, f, x, y, maxw, fill, gap=1.22, center=False, W=0):
    for l in wrap(d, text, f, maxw):
        xx = (W - d.textlength(l, font=f)) / 2 if center else x
        d.text((xx, y), l, font=f, fill=fill); y += int(f.size * gap)
    return y

def card(dr, path):
    it = dr["item"]; im = bg(1080, 1080, PALETTES[hash(it["name"]) % 4]); d = ImageDraw.Draw(im)
    d.rounded_rectangle((70, 70, 70 + d.textlength(it["src"], font=font(34)) + 50, 130), 30, fill=(255, 255, 255))
    d.text((95, 78), it["src"], font=font(34), fill=(20, 24, 32))
    y = para(d, dr.get("hook", ""), font(84), 70, 190, 940, (255, 255, 255), 1.1)
    y = para(d, dr.get("card_title", it["name"]), font(44, False), 70, y + 20, 940, (220, 230, 240)) + 30
    for p in dr.get("card_points", [])[:3]:
        d.ellipse((74, y + 16, 92, y + 34), fill=(255, 200, 80))
        y = para(d, p, font(42, False), 116, y, 880, (255, 255, 255)) + 16
    d.text((70, 960), it["name"], font=font(40), fill=(255, 255, 255))
    meta = f"{it['score']} stars/votes" + (f"   {it['lang']}" if it.get("lang") else "")
    d.text((70, 1010), meta, font=font(30, False), fill=(255, 215, 120))
    im.save(path); return path

def slide(text, idx, dr, path):
    it = dr["item"]; im = bg(1080, 1920, PALETTES[idx % 4]); d = ImageDraw.Draw(im)
    f = font(80 if len(text) < 90 else 64)
    lines = wrap(d, text, f, 900); y = (1920 - len(lines) * int(f.size * 1.25)) // 2 - 60
    for l in lines:
        d.text(((1080 - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(255, 255, 255)); y += int(f.size * 1.25)
    n = it["name"]; fn = font(44)
    d.text(((1080 - d.textlength(n, font=fn)) / 2, 1620), n, font=fn, fill=(255, 215, 120))
    sub = font(34, False); s = f"{it['src']}  |  {it['score']} stars/votes"
    d.text(((1080 - d.textlength(s, font=sub)) / 2, 1690), s, font=sub, fill=(230, 235, 240))
    im.save(path)

def video(dr, outdir):
    ff = imageio_ffmpeg.get_ffmpeg_exe(); voice = os.getenv("EDGE_VOICE", "en-US-AndrewNeural"); segs = []
    for i, line in enumerate(dr["script"]):
        png, mp3, seg = (os.path.join(outdir, f"s{i}.{e}") for e in ("png", "mp3", "mp4"))
        slide(line, i, dr, png)
        asyncio.run(edge_tts.Communicate(line, voice).save(mp3))
        dur = MP3(mp3).info.length + 0.4
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", png, "-i", mp3, "-vf",
            f"zoompan=z='min(zoom+0.0006,1.08)':d={int(dur * 30)}:s=1080x1920:fps=30,fade=t=in:d=0.3,format=yuv420p",
            "-af", "apad", "-t", f"{dur:.2f}", "-c:v", "libx264", "-c:a", "aac", "-ar", "44100", "-ac", "2", seg], check=True)
        segs.append(f"s{i}.mp4")
    with open(os.path.join(outdir, "list.txt"), "w") as f: f.write("\n".join(f"file '{s}'" for s in segs))
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "short.mp4"], cwd=outdir, check=True)
    return os.path.join(outdir, "short.mp4")
