#!/usr/bin/env python3
"""
Generate favicon assets for S-DNA branding.

Creates multi-format favicon suite:
- favicon.ico (16, 32, 64 px)
- favicon.svg (scalable)
- favicon-16x16.png, favicon-32x32.png
- apple-touch-icon.png (180x180)
- android-chrome-192x192.png
- android-chrome-512x512.png
- site.webmanifest (PWA metadata)

Color palette (S-DNA):
- Teal (primary): #00a7a0
- Blue (accent): #5b9bd5
- White (background)
"""

import io
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    exit(1)


def create_sdna_favicon(size: int, bg_white: bool = True) -> Image.Image:
    """
    Generate S-DNA favicon at given size.

    Args:
        size: Canvas size in pixels (e.g., 16, 32, 192, 512)
        bg_white: If True, use white background with rounded corners
                 If False, use transparent background

    Returns:
        PIL Image in RGBA mode
    """
    # Color palette
    TEAL = "#00a7a0"      # S-DNA primary
    BLUE = "#5b9bd5"      # Accent
    WHITE = "#ffffff"

    # Create image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_white:
        # White background with rounded corners
        radius = int(size * 0.15)  # ~15% of size for smooth rounded square
        # Draw rounded rectangle background
        draw.rounded_rectangle(
            [(0, 0), (size, size)],
            radius=radius,
            fill=WHITE
        )

    # Scale S-DNA monogram to fit in canvas (leave ~10% padding)
    padding = int(size * 0.10)
    available = size - (padding * 2)

    # Draw S-DNA monogram (stylized S)
    # Top curve of S
    top_left = (padding + int(available * 0.15), padding + int(available * 0.1))
    top_right = (padding + int(available * 0.85), padding + int(available * 0.35))

    # Draw teal S shape (simplified path)
    # Left side of S curve
    left_x = padding + int(available * 0.2)
    right_x = padding + int(available * 0.8)
    top_y = padding + int(available * 0.15)
    mid_y = padding + int(available * 0.5)
    bottom_y = padding + int(available * 0.85)

    stroke_width = max(1, int(size * 0.08))

    # Draw main S stroke (teal) using arcs approximated with lines
    # Upper arc of S
    draw.arc(
        [(left_x, top_y), (right_x, mid_y)],
        start=180,
        end=0,
        fill=TEAL,
        width=stroke_width
    )

    # Lower arc of S
    draw.arc(
        [(left_x, mid_y), (right_x, bottom_y)],
        start=0,
        end=180,
        fill=TEAL,
        width=stroke_width
    )

    # Blue accent shapes (small geometric accents top-right and bottom-left)
    accent_size = int(available * 0.2)

    # Top-right accent
    tr_x = right_x - accent_size
    tr_y = top_y
    draw.polygon(
        [(tr_x, tr_y), (right_x, tr_y), (right_x, tr_y + accent_size), (tr_x, tr_y + accent_size)],
        fill=BLUE
    )

    # Bottom-left accent
    bl_x = left_x
    bl_y = bottom_y - accent_size
    draw.polygon(
        [(bl_x, bl_y), (bl_x + accent_size, bl_y), (bl_x + accent_size, bottom_y), (bl_x, bottom_y)],
        fill=BLUE
    )

    return img


def generate_ico(sizes: list[int] = [16, 32, 64]) -> bytes:
    """Generate multi-resolution .ico file."""
    images = [create_sdna_favicon(s, bg_white=True) for s in sizes]

    ico_buffer = io.BytesIO()
    # PIL saves ICO with first image as primary, others as alternates
    images[0].save(
        ico_buffer,
        format="ICO",
        sizes=[(img.width, img.height) for img in images]
    )
    return ico_buffer.getvalue()


def generate_svg() -> str:
    """Generate scalable SVG favicon."""
    # SVG version of S-DNA (more precise vector)
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <!-- White rounded-square background -->
  <rect x="0" y="0" width="512" height="512" rx="76" fill="white"/>

  <!-- Teal S-DNA monogram -->
  <g transform="translate(256, 256) scale(1, 1)">
    <!-- Main S stroke (teal) -->
    <path d="M -80 -100 Q 0 -120 80 -80 Q 100 -60 100 -40 Q 100 -20 80 0 Q 0 40 -80 40 Q -100 40 -100 60 Q -100 80 -80 100 Q 0 120 80 100 Q 100 90 100 70"
          stroke="#00a7a0" stroke-width="50" fill="none" stroke-linecap="round" stroke-linejoin="round"/>

    <!-- Blue accent top-right -->
    <polygon points="40,-80 120,-80 120,0 40,0" fill="#5b9bd5"/>

    <!-- Blue accent bottom-left -->
    <polygon points="-120,40 -40,40 -40,120 -120,120" fill="#5b9bd5"/>
  </g>
</svg>'''
    return svg


def save_favicons(output_dir: str = "static"):
    """Generate and save all favicon assets."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("🎨 Generating S-DNA favicon assets...")

    # 1. Generate and save .ico (multi-resolution)
    print("  → Creating favicon.ico (16×16, 32×32, 64×64)...")
    ico_data = generate_ico([16, 32, 64])
    ico_path = output_path / "favicon.ico"
    ico_path.write_bytes(ico_data)
    print(f"    ✓ {ico_path}")

    # 2. Generate and save SVG
    print("  → Creating favicon.svg (scalable)...")
    svg_data = generate_svg()
    svg_path = output_path / "favicon.svg"
    svg_path.write_text(svg_data)
    print(f"    ✓ {svg_path}")

    # 3. PNG formats
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }

    for filename, size in sizes.items():
        print(f"  → Creating {filename} ({size}×{size})...")
        img = create_sdna_favicon(size, bg_white=True)
        img_path = output_path / filename
        # Convert RGBA to RGB for better compatibility, except for transparent cases
        if img.mode == "RGBA" and filename != "favicon-*":
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
            rgb_img.save(img_path, "PNG")
        else:
            img.save(img_path, "PNG")
        print(f"    ✓ {img_path}")

    # 4. Generate site.webmanifest (PWA)
    print("  → Creating site.webmanifest (PWA metadata)...")
    manifest = """{
  "name": "SEOMONEY",
  "short_name": "SEOMONEY",
  "description": "Blog công nghệ, tài chính cá nhân, du lịch và trải nghiệm cuộc sống",
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#ffffff",
  "background_color": "#ffffff",
  "display": "standalone",
  "scope": "/",
  "start_url": "/"
}"""
    manifest_path = output_path / "site.webmanifest"
    manifest_path.write_text(manifest)
    print(f"    ✓ {manifest_path}")

    print("\n✅ Favicon asset generation complete!")
    print(f"\nFiles created in {output_path}/:")
    for f in sorted(output_path.glob("*fav* *icon* site.webmanifest")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    save_favicons()
