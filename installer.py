"""
Create optimized logo files next to the original.
logo.png is 2.9 MB and shown at ~64px tall in the navbar.
We create:
  static/images/logo-opt.webp  — WebP at 2x display size (128px tall, proportional width)
  static/images/logo-opt.png   — PNG fallback at same size
The original static/images/logo.png is NOT modified.
"""
from PIL import Image
import os

SRC = r"static\images\logo.png"
WEBP_OUT = r"static\images\logo-opt.webp"
PNG_OUT  = r"static\images\logo-opt.png"

img = Image.open(SRC)
orig_w, orig_h = img.size
print(f"Original: {orig_w}x{orig_h}  {os.path.getsize(SRC):,} bytes")

# Display height is max 64px (navbar h-16 with max-h-16). 2× = 128px.
TARGET_H = 128
ratio = TARGET_H / orig_h
target_w = int(orig_w * ratio)
print(f"Resizing to: {target_w}x{TARGET_H}")

resized = img.resize((target_w, TARGET_H), Image.LANCZOS)

# WebP (lossy q=85, good quality, tiny file)
resized.save(WEBP_OUT, "WEBP", quality=85, method=6)
print(f"WebP: {os.path.getsize(WEBP_OUT):,} bytes  ({WEBP_OUT})")

# PNG fallback (optimize=True, 8-bit palette if RGBA → keep RGBA)
resized.save(PNG_OUT, "PNG", optimize=True)
print(f"PNG:  {os.path.getsize(PNG_OUT):,} bytes  ({PNG_OUT})")

print(f"\nSize reduction: {os.path.getsize(SRC):,} → {os.path.getsize(WEBP_OUT):,} bytes (WebP)")
print(f"Width of optimized logo: {target_w}px  (for width= attribute in HTML)")
