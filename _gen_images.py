"""Create local agriculture-themed SVG artwork and download sample photos."""

import os
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images")
os.makedirs(ROOT, exist_ok=True)


def bag(label, body, band):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#f3f8ef"/>
  <circle cx="540" cy="78" r="42" fill="#f6d365"/>
  <path d="M0 390c90-30 140-110 230-100s120 80 220 60 140-50 190-24v154H0z" fill="#d7ebc8"/>
  <path d="M48 430c40-70 20-120 8-150" fill="none" stroke="#7cb342" stroke-width="6" stroke-linecap="round"/>
  <path d="M78 420c18-60 8-100-8-140" fill="none" stroke="#2e7d32" stroke-width="6" stroke-linecap="round"/>
  <rect x="205" y="78" width="230" height="320" rx="22" fill="{body}"/>
  <path d="M205 132h230v34c-46 20-78 16-115-2s-74-14-115 2z" fill="{band}"/>
  <rect x="248" y="196" width="144" height="86" rx="10" fill="#fff8e1"/>
  <text x="320" y="248" text-anchor="middle" font-family="Georgia, serif" font-size="30" font-weight="700" fill="#14532d">{label}</text>
  <text x="320" y="330" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" letter-spacing="2" fill="#f7f3df">FERTILIZER</text>
</svg>"""


files = {
    "logo.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="16" fill="#14532d"/>
  <path d="M34 52c1-18 12-28 24-32-10 18-10 30-4 38-8-2-15-4-20-6z" fill="#f6d365"/>
  <path d="M30 52C28 30 16 18 6 14c8 16 14 26 20 38 2 0 4-6 4 0z" fill="#a5d6a7"/>
  <path d="M32 50v-24" stroke="#e8f5e9" stroke-width="3" stroke-linecap="round"/>
</svg>""",
    "default.svg": bag("FERT", "#2e7d32", "#1b5e20"),
    "urea.svg": bag("UREA", "#2e7d32", "#f6d365"),
    "dap.svg": bag("DAP", "#1565c0", "#0d47a1"),
    "npk.svg": bag("NPK", "#6a1b9a", "#4a148c"),
    "potash.svg": bag("POTASH", "#ef6c00", "#e65100"),
    "organic.svg": bag("ORGANIC", "#6d4c41", "#4e342e"),
    "ssp.svg": bag("SSP", "#00897b", "#00695c"),
    "micro.svg": bag("MICRO", "#c0a000", "#8d6e00"),
    "neem.svg": bag("NEEM", "#33691e", "#1b5e20"),
    "shop.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#f3f8ef"/>
  <rect x="70" y="150" width="500" height="250" rx="8" fill="#fff"/>
  <path d="M60 170 L320 60 L580 170 Z" fill="#14532d"/>
  <rect x="110" y="210" width="90" height="70" fill="#d7ebc8"/>
  <rect x="230" y="210" width="90" height="70" fill="#d7ebc8"/>
  <rect x="350" y="210" width="90" height="70" fill="#d7ebc8"/>
  <rect x="275" y="300" width="90" height="100" fill="#2e7d32"/>
  <circle cx="500" cy="90" r="28" fill="#f6d365"/>
  <text x="320" y="200" text-anchor="middle" font-family="Georgia, serif" font-size="28" fill="#14532d">FERTILIZER SHOP</text>
</svg>""",
    "about.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 480">
  <rect width="640" height="480" fill="#e8f5e9"/>
  <circle cx="520" cy="90" r="48" fill="#f6d365"/>
  <path d="M0 360c120-80 180-40 260-20s140-20 220 20 120 10 160-10v130H0z" fill="#7cb342"/>
  <path d="M0 410c140-40 220-10 320 0s180-20 320 10v70H0z" fill="#2e7d32"/>
  <rect x="300" y="250" width="18" height="110" fill="#6d4c41"/>
  <circle cx="309" cy="230" r="46" fill="#43a047"/>
  <text x="48" y="80" font-family="Georgia, serif" font-size="36" fill="#14532d">Grown with care</text>
</svg>""",
}

for name, content in files.items():
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as handle:
        handle.write(content)

photos = {
    "hero.jpg": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1600&q=70",
    "about.jpg": "https://images.unsplash.com/photo-1560493676-04071c5f467b?auto=format&fit=crop&w=1200&q=70",
    "shop.jpg": "https://images.unsplash.com/photo-1488459716781-31db52582fe9?auto=format&fit=crop&w=1000&q=70",
    "urea.jpg": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?auto=format&fit=crop&w=1000&q=70",
    "dap.jpg": "https://images.unsplash.com/photo-1574943320219-553eb213f72d?auto=format&fit=crop&w=1000&q=70",
    "npk.jpg": "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=1000&q=70",
    "potash.jpg": "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1000&q=70",
    "organic.jpg": "https://images.unsplash.com/photo-1605000797499-95a51c5269ae?auto=format&fit=crop&w=1000&q=70",
    "ssp.jpg": "https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?auto=format&fit=crop&w=1000&q=70",
    "micro.jpg": "https://images.unsplash.com/photo-1591857177580-dc82b9ac4e1e?auto=format&fit=crop&w=1000&q=70",
    "neem.jpg": "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=1000&q=70",
}

opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", "SmartFertilizerFinder/1.0")]
for name, url in photos.items():
    destination = os.path.join(ROOT, name)
    try:
        with opener.open(url, timeout=25) as response:
            data = response.read()
        if len(data) < 2000:
            raise RuntimeError("response too small")
        with open(destination, "wb") as handle:
            handle.write(data)
        print(f"saved {name} ({len(data)} bytes)")
    except Exception as exc:
        print(f"skip {name}: {exc}")
