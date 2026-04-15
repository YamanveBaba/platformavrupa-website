# -*- coding: utf-8 -*-
"""
Platform saglik raporunu kisa MP4 olarak uretir (slayt + FFmpeg).

  python platform_rapor_videosu.py
  python platform_rapor_videosu.py --no-supabase
  python platform_rapor_videosu.py --cikti C:\\temp\\rapor.mp4

Gereksinim: pip install pillow requests
           ffmpeg PATH'te olmali
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("HATA: pip install pillow")
    sys.exit(1)

from platform_karsi_lastir_tani import (
    tani_adzuna,
    tani_arbeitnow,
    tani_bundesagentur,
    tani_cevirmen,
    tani_jobicy,
    tani_remotive,
    tani_supabase,
)


def _font(boyut: int) -> ImageFont.FreeTypeFont:
    for yol in (
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.isfile(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except OSError:
                continue
    return ImageFont.load_default()


def _metin_genislik(draw: ImageDraw.ImageDraw, metin: str, font: ImageFont.FreeTypeFont) -> float:
    try:
        return float(draw.textlength(metin, font=font))
    except Exception:
        b = draw.textbbox((0, 0), metin, font=font)
        return float(b[2] - b[0])


def _satir_parcalari(metin: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, genislik: int) -> list[str]:
    metin = (metin or "").replace("\r", " ")
    kelimeler = metin.split()
    if not kelimeler:
        return [""]
    satirlar: list[str] = []
    cur = ""
    for w in kelimeler:
        test = (cur + " " + w).strip()
        if _metin_genislik(draw, test, font) <= genislik:
            cur = test
        else:
            if cur:
                satirlar.append(cur)
            cur = w
    if cur:
        satirlar.append(cur)
    return satirlar if satirlar else [""]


def _ciz_kare(
    w: int,
    h: int,
    baslik: str,
    detay_satirlari: list[str],
    alt_not: Optional[str],
    ok: bool,
) -> Image.Image:
    arka = (22, 22, 38)
    img = Image.new("RGB", (w, h), arka)
    draw = ImageDraw.Draw(img)
    f_buyuk = _font(46)
    f_orta = _font(30)
    f_kucuk = _font(24)
    renk_baslik = (230, 230,238)
    renk_ok = (80, 200, 120)
    renk_hata = (240, 90, 90)

    draw.rectangle([40, 40, w - 40, 120], outline=(60, 60, 90), width=2)
    draw.text((60, 55), baslik[:80], fill=renk_baslik, font=f_buyuk)

    badge = "CALISIYOR" if ok else "SORUN"
    f_rozet = _font(52)
    draw.text((60, 140), badge, fill=renk_ok if ok else renk_hata, font=f_rozet)

    y = 220
    for sat in detay_satirlari[:14]:
        for parca in _satir_parcalari(sat, draw, f_orta, w - 120):
            draw.text((60, y), parca[:120], fill=(200, 200, 210), font=f_orta)
            y += 38
            if y > h - 160:
                break
        if y > h - 160:
            break

    if alt_not:
        y = h - 100
        for parca in _satir_parcalari(f"Not: {alt_not}", draw, f_kucuk, w - 120):
            draw.text((60, y), parca[:140], fill=(180, 160, 120), font=f_kucuk)
            y += 30

    return img


def _intro_kare(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), (18, 18, 32))
    draw = ImageDraw.Draw(img)
    fb = _font(56)
    fo = _font(32)
    draw.text((80, 200), "Platform Avrupa", fill=(255, 200, 100), font=fb)
    draw.text(
        (80, 300),
        "Baglanti saglik raporu (video)",
        fill=(200, 200, 220),
        font=fo,
    )
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    draw.text((80, 380), dt, fill=(150, 150, 170), font=fo)
    return img


def _ozet_kare(w: int, h: int, raporlar: list[dict]) -> Image.Image:
    img = Image.new("RGB", (w, h), (18, 18, 32))
    draw = ImageDraw.Draw(img)
    fb = _font(44)
    fo = _font(28)
    bas = sum(1 for r in raporlar if r.get("ok"))
    top = len(raporlar)
    draw.text((80, 120), "Ozet", fill=(255, 200, 100), font=fb)
    draw.text((80, 200), f"{bas} / {top} bolum sorunsuz", fill=(200, 220, 200), font=fo)
    y = 280
    for r in raporlar:
        ad = (r.get("urun") or "?")[:45]
        ok = r.get("ok")
        isaret = "[OK]" if ok else "[!!]"
        renk = (120, 200, 140) if ok else (240, 120, 120)
        draw.text((80, y), f"{isaret} {ad}", fill=renk, font=fo)
        y += 40
        if y > h - 60:
            break
    return img


def rapor_topla(no_supabase: bool) -> list[dict]:
    from is_ilani_cekici import ADZUNA_ID, ADZUNA_KEY

    sira: list[dict] = []
    sira.append(tani_arbeitnow())
    sira.append(tani_adzuna(ADZUNA_ID, ADZUNA_KEY))
    sira.append(tani_bundesagentur())
    sira.append(tani_jobicy())
    sira.append(tani_remotive())
    if not no_supabase:
        sira.append(tani_supabase())
    sira.append(tani_cevirmen())
    return sira


def videoya_cevir(
    raporlar: list[dict],
    cikti: str,
    slayt_sn: float,
    w: int,
    h: int,
) -> None:
    if not shutil.which("ffmpeg"):
        print("HATA: ffmpeg bulunamadi. PATH'e ekleyin.")
        sys.exit(1)

    tmp = tempfile.mkdtemp(prefix="platform_rapor_")
    try:
        png_yollari: list[str] = []
        intro = os.path.join(tmp, "slide_000.png")
        _intro_kare(w, h).save(intro, "PNG")
        png_yollari.append(intro)

        for i, r in enumerate(raporlar, start=1):
            baslik = str(r.get("urun", ""))
            ok = bool(r.get("ok"))
            ozet = str(r.get("ozet", ""))
            ms = r.get("sure_ms", 0)
            detay = [
                f"Sure: {ms:.0f} ms",
                "",
                ozet,
            ]
            alt = str(r["not"]) if r.get("not") else None
            p = os.path.join(tmp, f"slide_{i:03d}.png")
            _ciz_kare(w, h, baslik, detay, alt, ok).save(p, "PNG")
            png_yollari.append(p)

        ozet_p = os.path.join(tmp, f"slide_{len(raporlar)+1:03d}.png")
        _ozet_kare(w, h, raporlar).save(ozet_p, "PNG")
        png_yollari.append(ozet_p)

        segmentler: list[str] = []
        for idx, p in enumerate(png_yollari):
            seg = os.path.join(tmp, f"seg_{idx:03d}.mp4")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    p,
                    "-t",
                    f"{slayt_sn:.3f}",
                    "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-an",
                    seg,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            segmentler.append(seg)

        concat = os.path.join(tmp, "vconcat.txt")
        with open(concat, "w", encoding="utf-8") as f:
            for seg in segmentler:
                f.write(f"file '{os.path.abspath(seg).replace(chr(92), '/')}'\n")

        birlesik = os.path.join(tmp, "birlesik_nosound.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat,
                "-c",
                "copy",
                birlesik,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        topt = len(segmentler) * slayt_sn + 0.5
        mute = os.path.join(tmp, "mute.aac")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=mono",
                "-t",
                f"{topt:.1f}",
                "-c:a",
                "aac",
                mute,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                birlesik,
                "-i",
                mute,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                cikti,
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(r.stderr[:2500])
            raise RuntimeError("ffmpeg video basarisiz")

        print(f"Video kaydedildi: {cikti}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Platform rapor MP4")
    ap.add_argument("--no-supabase", action="store_true")
    ap.add_argument("--cikti", default="", help="Cikti dosyasi (.mp4)")
    ap.add_argument("--slayt-sn", type=float, default=4.0, help="Her slayt suresi")
    args = ap.parse_args()

    cikti = args.cikti.strip()
    if not cikti:
        cikti = os.path.join(SCRIPT_DIR, "platform_saglik_raporu.mp4")

    print("Testler calisiyor (biraz surebilir)...")
    rapor = rapor_topla(no_supabase=args.no_supabase)
    print(f"{len(rapor)} bolum toplandi, video uretiliyor...")
    videoya_cevir(rapor, cikti, args.slayt_sn, 1280, 720)


if __name__ == "__main__":
    main()
