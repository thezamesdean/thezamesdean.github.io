#!/usr/bin/env python3
"""쇼츠 자동 생성기 (비포/애프터, 랭킹).

사용법:
    python3 make_short.py examples/before_after.json
    python3 make_short.py examples/ranking.json -o out/ranking.mp4

필요 패키지: pip install pillow numpy imageio-ffmpeg
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

W, H = 1080, 1920
FPS = 30
SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "BlackHanSans-Regular.ttf")

YELLOW = (255, 221, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (235, 64, 52)
GREEN = (46, 204, 113)


# ---------- 유틸 ----------

def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):
    """살짝 튕기는 팝 효과."""
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def font(size):
    return ImageFont.truetype(FONT, size)


def fit_font(text, max_w, size, min_size=30):
    while size > min_size:
        f = font(size)
        if f.getbbox(text)[2] <= max_w:
            return f
        size -= 4
    return font(min_size)


def text_layer(text, size, fill=WHITE, stroke=0, stroke_fill=BLACK, max_w=W - 80):
    """글자를 RGBA 레이어로 미리 그려둔다 (애니메이션 때 크기만 조절)."""
    f = fit_font(text, max_w - stroke * 2, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    img = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2 - l, 2 - t), text, font=f, fill=fill,
                             stroke_width=stroke, stroke_fill=stroke_fill)
    return img


def pill_layer(text, size, bg, fg=WHITE, pad=(34, 16)):
    f = font(size)
    l, t, r, b = f.getbbox(text)
    img = Image.new("RGBA", (r - l + pad[0] * 2, b - t + pad[1] * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=img.height // 2, fill=bg)
    d.text((pad[0] - l, pad[1] - t), text, font=f, fill=fg)
    return img


def paste_scaled(canvas, layer, cx, cy, scale=1.0, alpha=1.0):
    """layer를 (cx, cy) 중심에 scale/alpha 적용해서 붙인다."""
    if scale <= 0.01 or alpha <= 0.01:
        return
    if abs(scale - 1) > 0.01:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))),
                             Image.BILINEAR)
    if alpha < 0.99:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


class Media:
    """이미지를 영역 크기에 맞게 꽉 채우고(cover) 천천히 줌인한다."""

    def __init__(self, path, w, h, max_zoom=1.12, placeholder=None):
        self.w, self.h = w, h
        if path and os.path.exists(path):
            src = Image.open(path).convert("RGB")
        else:
            src = make_placeholder(placeholder or os.path.basename(str(path)), w, h)
        # 최대 줌 크기로 미리 한 번만 리사이즈
        tw, th = int(w * max_zoom), int(h * max_zoom)
        s = max(tw / src.width, th / src.height)
        src = src.resize((math.ceil(src.width * s), math.ceil(src.height * s)), Image.LANCZOS)
        self.src = src
        self.max_zoom = max_zoom

    def frame(self, zoom=1.0):
        zoom = max(1.0, min(self.max_zoom, zoom))
        # zoom=1이면 영역 전체, max_zoom이면 원본 1:1 크기로 가운데를 잘라낸다
        cw = min(self.w * self.max_zoom / zoom, self.src.width)
        ch = min(self.h * self.max_zoom / zoom, self.src.height)
        x0 = (self.src.width - cw) / 2
        y0 = (self.src.height - ch) / 2
        return self.src.resize((self.w, self.h), Image.BILINEAR,
                               box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")


def make_placeholder(label, w, h):
    """사진이 없을 때 쓰는 샘플 이미지."""
    rng = np.random.default_rng(abs(hash(label)) % (2 ** 32))
    c1, c2 = rng.integers(40, 200, 3), rng.integers(40, 200, 3)
    yy = np.linspace(0, 1, h)[:, None, None]
    arr = (c1 * (1 - yy) + c2 * yy).astype(np.uint8)
    arr = np.broadcast_to(arr, (h, w, 3)).copy()
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    f = fit_font(label, w - 120, 120)
    d.text((w / 2, h / 2), label, font=f, fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=BLACK)
    return img


def title_bar(lines, height, colors=(WHITE, YELLOW)):
    """상단 검은 바 + 후킹 문구 (최대 2~3줄)."""
    bar = Image.new("RGBA", (W, height), (0, 0, 0, 255))
    lines = [ln for ln in lines if ln]
    if not lines:
        return bar
    layers = [text_layer(ln, 96, fill=colors[min(i, len(colors) - 1)], max_w=W - 60)
              for i, ln in enumerate(lines)]
    gap = 18
    total = sum(l.height for l in layers) + gap * (len(layers) - 1)
    y = (height - total) / 2
    for l in layers:
        bar.alpha_composite(l, (int((W - l.width) / 2), int(y)))
        y += l.height + gap
    return bar


# ---------- 효과음 ----------

def sfx_whoosh(dur=0.5):
    n = int(SR * dur)
    noise = np.random.default_rng(1).standard_normal(n)
    env = np.sin(np.linspace(0, math.pi, n)) ** 2
    # 간단한 로우패스로 부드럽게
    k = np.ones(40) / 40
    return np.convolve(noise, k, mode="same") * env * 0.9


def sfx_pop(freq=520, dur=0.18):
    t = np.arange(int(SR * dur)) / SR
    f = freq * (1 + 1.5 * np.exp(-t * 30))
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * 0.6


def sfx_boom(dur=0.6):
    t = np.arange(int(SR * dur)) / SR
    f = 110 * np.exp(-t * 4) + 40
    return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.9


def write_sfx(events, total, path):
    buf = np.zeros(int(SR * total) + SR)
    for t0, snd in events:
        i = int(t0 * SR)
        buf[i:i + len(snd)] += snd[:len(buf) - i]
    buf = np.clip(buf, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32000).astype(np.int16).tobytes())


# ---------- 렌더링 ----------

def render(frame_fn, total, out, sfx_events, music=None, music_volume=0.6):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = tempfile.mkdtemp()
    silent = os.path.join(tmp, "v.mp4")
    sfx = os.path.join(tmp, "sfx.wav")
    write_sfx(sfx_events, total, sfx)

    p = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                          "-preset", "medium", silent], stdin=subprocess.PIPE)
    n = int(total * FPS)
    for i in range(n):
        p.stdin.write(frame_fn(i / FPS).convert("RGB").tobytes())
        if i % FPS == 0:
            print(f"\r  렌더링 {i / n * 100:5.1f}%", end="", flush=True)
    p.stdin.close()
    p.wait()
    print("\r  렌더링 100.0%")

    cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", silent, "-i", sfx]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music, "-filter_complex",
                f"[2:a]volume={music_volume},afade=t=out:st={max(0, total - 1)}:d=1[m];"
                f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total}", out]
    subprocess.run(cmd, check=True)
    print(f"완료: {out}")


# ---------- 비포/애프터 ----------

def before_after(cfg, base):
    T = cfg.get("timing", {})
    t_before = T.get("before", 3.5)      # 비포 노출
    t_trans = T.get("transition", 0.6)   # 와이프 전환
    t_after = T.get("after", 4.0)        # 애프터 노출
    t_split = T.get("split", 3.0)        # 좌우 비교 (0이면 생략)
    total = t_before + t_trans + t_after + t_split

    top = 380
    mh = H - top
    b, a = cfg["before"], cfg["after"]
    rp = lambda p: os.path.join(base, p) if p else None
    mb = Media(rp(b.get("image")), W, mh, placeholder="BEFORE 사진")
    ma = Media(rp(a.get("image")), W, mh, placeholder="AFTER 사진")
    sb = Media(rp(b.get("image")), W // 2, mh, placeholder="BEFORE")
    sa = Media(rp(a.get("image")), W // 2, mh, placeholder="AFTER")

    bar = title_bar(cfg.get("hook", []), top)
    pill_b = pill_layer(b.get("label", "BEFORE"), 64, RED)
    pill_a = pill_layer(a.get("label", "AFTER"), 64, GREEN)
    small_b = pill_layer(b.get("label", "BEFORE"), 46, RED)
    small_a = pill_layer(a.get("label", "AFTER"), 46, GREEN)
    cap_b = text_layer(b.get("caption", ""), 120, WHITE, 8) if b.get("caption") else None
    cap_a = text_layer(a.get("caption", ""), 130, YELLOW, 8) if a.get("caption") else None
    scap_b = text_layer(b.get("caption", ""), 70, WHITE, 6, max_w=W // 2 - 30) if b.get("caption") else None
    scap_a = text_layer(a.get("caption", ""), 70, YELLOW, 6, max_w=W // 2 - 30) if a.get("caption") else None
    bottom = text_layer(cfg["bottom"], 72, WHITE, 7) if cfg.get("bottom") else None

    s1 = t_before
    s2 = s1 + t_trans
    s3 = s2 + t_after
    cap_y = top + mh * 0.80

    def frame(t):
        c = Image.new("RGBA", (W, H), BLACK + (255,))
        if t < s1:
            c.alpha_composite(mb.frame(1 + 0.06 * t / s1), (0, top))
            paste_scaled(c, pill_b, 60 + pill_b.width / 2, top + 90, ease_back(t / 0.35))
            if cap_b:
                paste_scaled(c, cap_b, W / 2, cap_y, ease_back((t - 0.3) / 0.35))
        elif t < s2:
            p = ease_out((t - s1) / t_trans)
            c.alpha_composite(mb.frame(1.06), (0, top))
            x = int(W * p)
            if x > 0:
                c.alpha_composite(ma.frame(1.0).crop((0, 0, x, mh)), (0, top))
            ImageDraw.Draw(c).rectangle([x - 8, top, x + 8, H], fill=WHITE)
        elif t < s3 or t_split <= 0:
            lt = t - s2
            c.alpha_composite(ma.frame(1 + 0.06 * lt / t_after), (0, top))
            flash = max(0.0, 1 - lt / 0.25)
            if flash > 0:
                c.alpha_composite(Image.new("RGBA", (W, mh), (255, 255, 255, int(200 * flash))), (0, top))
            paste_scaled(c, pill_a, 60 + pill_a.width / 2, top + 90, ease_back(lt / 0.35))
            if cap_a:
                paste_scaled(c, cap_a, W / 2, cap_y, ease_back((lt - 0.2) / 0.4))
        else:
            lt = t - s3
            p = ease_out(lt / 0.45)
            off = int((1 - p) * W / 2)
            c.alpha_composite(sb.frame(1.0), (-off, top))
            c.alpha_composite(sa.frame(1.0), (W // 2 + off, top))
            ImageDraw.Draw(c).rectangle([W // 2 - 5, top, W // 2 + 4, H], fill=WHITE)
            paste_scaled(c, small_b, W / 4 - off, top + 80)
            paste_scaled(c, small_a, W * 3 / 4 + off, top + 80)
            if scap_b:
                paste_scaled(c, scap_b, W / 4 - off, cap_y)
            if scap_a:
                paste_scaled(c, scap_a, W * 3 / 4 + off, cap_y)
            if bottom:
                paste_scaled(c, bottom, W / 2, top + mh * 0.62, ease_back((lt - 0.5) / 0.4))
        # 상단 후킹 바 (시작할 때 살짝 튀어나옴)
        hs = 0.9 + 0.1 * ease_back(t / 0.3)
        if hs < 0.999:
            c.alpha_composite(Image.new("RGBA", (W, top), BLACK + (255,)), (0, 0))
            paste_scaled(c, bar, W / 2, top / 2, hs)
        else:
            c.alpha_composite(bar, (0, 0))
        return c

    events = [(0.0, sfx_pop(700)), (s1 - 0.1, sfx_whoosh()), (s2, sfx_boom())]
    if t_split > 0:
        events.append((s3, sfx_whoosh(0.4)))
    return frame, total, events


# ---------- 랭킹 ----------

def ranking(cfg, base):
    items = sorted(cfg["items"], key=lambda it: -it["rank"])  # N위 -> 1위 순서로 공개
    n = len(items)
    per = cfg.get("per_item", 2.6)
    intro = cfg.get("intro", 1.2)
    outro = cfg.get("outro", 1.5)
    first_bonus = cfg.get("first_bonus", 1.5)  # 1위는 더 오래
    durs = [per * (first_bonus if it["rank"] == 1 else 1) for it in items]
    starts = [intro + sum(durs[:i]) for i in range(n)]
    total = intro + sum(durs) + outro

    top = 360
    mh = H - top
    rp = lambda p: os.path.join(base, p) if p else None
    medias = [Media(rp(it.get("image")), W, mh, placeholder=f"{it['rank']}위 사진") for it in items]
    bar = title_bar(cfg.get("title", []), top)

    # 순위 목록 (1위가 맨 위)
    by_rank = {it["rank"]: it for it in items}
    ranks = sorted(by_rank)
    row_h = min(120, int((mh * 0.62) / max(1, n)))
    list_y0 = top + 60
    fs = int(row_h * 0.62)
    num_layers = {r: text_layer(f"{r}.", fs, WHITE, 6) for r in ranks}
    name_layers = {r: text_layer(by_rank[r]["name"], fs, WHITE, 6, max_w=W - 220) for r in ranks}
    name_hl = {r: text_layer(by_rank[r]["name"], fs, YELLOW, 6, max_w=W - 220) for r in ranks}
    big_rank = {r: text_layer(f"{r}위", 260, YELLOW if r != 1 else (255, 90, 60), 14) for r in ranks}
    descs = {r: text_layer(by_rank[r]["desc"], 64, WHITE, 6) for r in ranks if by_rank[r].get("desc")}
    outro_txt = text_layer(cfg["outro_text"], 80, YELLOW, 8) if cfg.get("outro_text") else None

    def frame(t):
        c = Image.new("RGBA", (W, H), BLACK + (255,))
        cur = -1
        for i, s in enumerate(starts):
            if t >= s:
                cur = i
        if cur >= 0:
            lt = t - starts[cur]
            c.alpha_composite(medias[cur].frame(1 + 0.08 * min(1, lt / durs[cur])), (0, top))
            # 목록 가독성을 위한 왼쪽 그림자
            fade = Image.new("RGBA", (W, mh), (0, 0, 0, 0))
            ImageDraw.Draw(fade).rectangle([0, 0, W, int(row_h * n + 120)], fill=(0, 0, 0, 90))
            c.alpha_composite(fade, (0, top))
        else:
            ImageDraw.Draw(c).rectangle([0, top, W, H], fill=(20, 20, 20))

        revealed = {items[i]["rank"]: starts[i] for i in range(cur + 1)}
        for j, r in enumerate(ranks):
            y = list_y0 + j * row_h + row_h / 2
            nl = num_layers[r]
            c.alpha_composite(nl, (40, int(y - nl.height / 2)))
            if r in revealed:
                lt = t - revealed[r] - 0.55  # 큰 숫자 뒤에 이름 등장
                if lt > 0:
                    lay = name_hl[r] if (cur >= 0 and items[cur]["rank"] == r) else name_layers[r]
                    sc = ease_back(lt / 0.3)
                    paste_scaled(c, lay, 150 + lay.width * sc / 2, y, sc)

        if cur >= 0:
            r = items[cur]["rank"]
            lt = t - starts[cur]
            if lt < 0.75:  # "N위" 크게 팝
                a = 1 if lt < 0.55 else 1 - (lt - 0.55) / 0.2
                paste_scaled(c, big_rank[r], W / 2, top + mh * 0.55, ease_back(lt / 0.3) * 1.0, a)
            if r in descs and lt > 0.6 and not (outro_txt and t > total - outro):
                paste_scaled(c, descs[r], W / 2, H - 220, ease_back((lt - 0.6) / 0.3))
        if outro_txt and t > total - outro:
            paste_scaled(c, outro_txt, W / 2, H - 220, ease_back((t - total + outro) / 0.35))

        c.alpha_composite(bar, (0, 0))
        return c

    events = [(0.0, sfx_pop(700))]
    for it, s in zip(items, starts):
        events.append((s, sfx_boom() if it["rank"] == 1 else sfx_whoosh(0.35)))
        events.append((s + 0.55, sfx_pop(500 + 60 * (n - it["rank"]))))
    return frame, total, events


def main():
    ap = argparse.ArgumentParser(description="비포/애프터·랭킹 쇼츠 생성기")
    ap.add_argument("config", help="JSON 설정 파일")
    ap.add_argument("-o", "--out", help="출력 mp4 경로")
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(args.config))
    kind = cfg.get("type")
    if kind == "before_after":
        frame, total, events = before_after(cfg, base)
    elif kind == "ranking":
        frame, total, events = ranking(cfg, base)
    else:
        sys.exit("type은 before_after 또는 ranking 이어야 합니다")

    out = args.out or os.path.join(HERE, "out", os.path.splitext(os.path.basename(args.config))[0] + ".mp4")
    music = os.path.join(base, cfg["music"]) if cfg.get("music") else None
    print(f"{kind} · {total:.1f}초")
    render(frame, total, out, events, music, cfg.get("music_volume", 0.6))


if __name__ == "__main__":
    main()
