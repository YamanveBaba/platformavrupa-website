# Colruyt Producten HTML'deki ürün kartı sayısını sayar (kullan at)
import re
import glob
import os

downloads = os.path.expanduser(r"~\Downloads")
pattern = os.path.join(downloads, "Producten*Colruyt*.html")
files = sorted(glob.glob(pattern))
if not files:
    print("Downloads'ta Producten Colruyt HTML bulunamadı.")
else:
    for path in files:
        name = os.path.basename(path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        # Sadece ana grid (Assortmentoverview-Page-0) icinde say
        match = re.search(
            r'id=Assortmentoverview-Page-0[^>]*>(.*?)</div>\s*</div>\s*<div class="load-more',
            html,
            re.DOTALL,
        )
        if match:
            grid_html = match.group(1)
            n_card = len(re.findall(r"card card--article", grid_html))
            n_retail = len(re.findall(r"retailproductnumber=\d+", grid_html))
            print(name.encode("ascii", "replace").decode())
            print(f"  [sadece grid] card--article: {n_card}, retailproductnumber: {n_retail}")
        else:
            n_card = len(re.findall(r"card card--article", html))
            n_retail = len(re.findall(r"retailproductnumber=\d+", html))
            print(name.encode("ascii", "replace").decode())
            print(f"  [tum sayfa] card--article: {n_card}, retailproductnumber: {n_retail}")
