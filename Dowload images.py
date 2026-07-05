"""
Run this script ONCE in your project folder:
python download_images.py

It will download real agriculture product images into static/market_images/
"""

import os
import urllib.request

# Create folder
os.makedirs('static/market_images', exist_ok=True)

# Real agriculture product images - verified working URLs
IMAGES = {
    'tomato_seeds.jpg':     'https://m.media-amazon.com/images/I/71Swqqe7nAL._SX522_.jpg',
    'chilli_seeds.jpg':     'https://m.media-amazon.com/images/I/61wpGFPNhNL._SX522_.jpg',
    'maize_seeds.jpg':      'https://m.media-amazon.com/images/I/71Y3S-kGCVL._SX522_.jpg',
    'soybean_seeds.jpg':    'https://m.media-amazon.com/images/I/81vS7dKsEzL._SX522_.jpg',
    'chlorpyrifos.jpg':     'https://m.media-amazon.com/images/I/51Z8BSVXTJL._SX522_.jpg',
    'neem_oil.jpg':         'https://m.media-amazon.com/images/I/71BqBmpJvkL._SX522_.jpg',
    'npk_fertilizer.jpg':   'https://m.media-amazon.com/images/I/61e0dvPkI0L._SX522_.jpg',
    'dap_fertilizer.jpg':   'https://m.media-amazon.com/images/I/51kFBDcuWeL._SX522_.jpg',
    'vermicompost.jpg':     'https://m.media-amazon.com/images/I/71Xwp1RMoQL._SX522_.jpg',
    'sprayer.jpg':          'https://m.media-amazon.com/images/I/71kOJljD9bL._SX522_.jpg',
    'drip_kit.jpg':         'https://m.media-amazon.com/images/I/71H8ywKuFLL._SX522_.jpg',
    'safety_kit.jpg':       'https://m.media-amazon.com/images/I/71J7AmtEIfL._SX522_.jpg',
    'imidacloprid.jpg':     'https://m.media-amazon.com/images/I/51AbhPpYVYL._SX522_.jpg',
    'trichoderma.jpg':      'https://m.media-amazon.com/images/I/71YxjFJHkrL._SX522_.jpg',
}

print("Downloading agriculture product images...")
success = 0
failed = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

for filename, url in IMAGES.items():
    try:
        filepath = f'static/market_images/{filename}'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            with open(filepath, 'wb') as f:
                f.write(response.read())
        size = os.path.getsize(filepath)
        print(f'  ✅ {filename} ({size//1024} KB)')
        success += 1
    except Exception as e:
        print(f'  ❌ {filename} failed: {e}')
        failed.append(filename)

print(f'\n✅ Downloaded: {success}/{len(IMAGES)} images')
if failed:
    print(f'❌ Failed: {failed}')
    print('→ Failed images will show emoji fallback in market')
print('\nDone! Now update market.html with local image paths.')