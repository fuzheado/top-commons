"""Display Commons images as ASCII art in the terminal."""
import urllib.request
import struct
from io import BytesIO

# ─── ASCII art from raw image (no Pillow needed) ──────────────
# We'll download the JPEG, use a minimal parser to get pixel brightness
# and render as ASCII

def _parse_jpeg_quick(data, max_pixels=8000):
    """
    Quick-and-dirty JPEG luminance extractor.
    Skips to SOF0 marker, reads dimensions, then samples.
    Falls back to just reporting dimensions if we can't parse.
    """
    # Very basic approach: download, use 'file' to verify, return dimensions
    # and a rough grid from a binary approach
    
    # Find SOF0 marker (0xFF 0xC0)
    i = 0
    while i < len(data) - 1:
        if data[i] == 0xFF:
            if data[i+1] == 0xC0:
                # SOF0 found
                precision = data[i+5]
                height = (data[i+6] << 8) | data[i+7]
                width = (data[i+8] << 8) | data[i+9]
                
                # Now extract luminance from the raw data
                # For a quick approach, scan through the compressed data
                # and sample bytes proportionally
                
                # Calculate scan size
                scan_start = i + 11  # after SOF0 header
                # Skip to SOS (Start of Scan) - 0xFF 0xDA
                j = scan_start
                while j < len(data) - 1:
                    if data[j] == 0xFF and data[j+1] == 0xDA:
                        sos_start = j
                        break
                    j += 1
                
                # Sample from the compressed data after SOS + header
                scan_data = data[sos_start+2:]
                if len(scan_data) < 16:
                    scan_data = data[:min(len(data), 100000)]
                
                # Calculate sample interval
                sample_count = min(max_pixels, width * height // 32)
                interval = max(1, len(scan_data) // sample_count)
                
                pixels = []
                for k in range(0, min(len(scan_data), sample_count * interval), interval):
                    # Use byte value as proxy for luminance
                    val = scan_data[k]
                    if isinstance(val, int):
                        pixels.append(val / 255.0)
                
                return width, height, pixels
            
            # Skip marker length if applicable
            if data[i+1] in range(0xC0, 0xCF):
                if i + 3 < len(data):
                    length = (data[i+2] << 8) | data[i+3]
                    i += length + 2
                    continue
            if data[i+1] in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9):
                i += 2
                continue
            if data[i+1] >= 0xE0 and data[i+1] <= 0xEF:
                if i + 3 < len(data):
                    length = (data[i+2] << 8) | data[i+3]
                    i += length + 2
                    continue
        i += 1
    return None, None, None


def ascii_art(data, ascii_width=40, charset='dense'):
    """Generate ASCII art from image bytes using chafa as backend."""
    import tempfile, subprocess, os
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(data)
        tmp_path = f.name
    
    try:
        # Run chafa with very compact settings, capture output
        ascii_height = max(3, ascii_width // 4)
        result = subprocess.run(
            ['chafa', '--symbols', 'block', '-s', str(ascii_width), '--color-space', 'rgb', tmp_path],
            capture_output=True, timeout=10
        )
        output = result.stdout.decode('utf-8', errors='replace')
        
        # Strip all ANSI escape sequences completely
        import re
        # Remove all escape sequences
        cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
        cleaned = re.sub(r'\x1b\].*?\x1b\\', '', cleaned)
        cleaned = re.sub(r'\x1b\[[0-9;]*m', '', cleaned)
        cleaned = re.sub(r'\x1b\[[0-9;]*[HJK]', '', cleaned)
        cleaned = re.sub(r'\x1b\][0-9;]*[^\x1b]*', '', cleaned)
        # Remove any remaining escape sequences
        cleaned = re.sub(r'\x1b\[[0-9;]*', '', cleaned)
        cleaned = re.sub(r'\x1b', '', cleaned)
        
        lines = [l for l in cleaned.split('\n') if l.strip()]
        return '\n'.join(lines[:ascii_height*2])
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def download_thumbnail(filename, width=200):
    """Download a Commons file thumbnail."""
    import urllib.parse
    
    encoded = urllib.parse.quote(filename)
    api_url = (f"https://commons.wikimedia.org/w/api.php"
               f"?action=query&format=json&prop=imageinfo"
               f"&iiprop=url&iilimit=1&iiurlwidth={width}"
               f"&titles=File:{encoded}")
    
    req = urllib.request.Request(api_url, headers={'User-Agent': 'TopCommons/1.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    import json
    data = json.loads(resp.read())
    
    for pid, pdata in data.get('query', {}).get('pages', {}).items():
        if 'imageinfo' in pdata:
            thumb_url = pdata['imageinfo'][0].get('thumburl')
            if thumb_url:
                req2 = urllib.request.Request(thumb_url, headers={'User-Agent': 'TopCommons/1.0'})
                resp2 = urllib.request.urlopen(req2, timeout=15)
                return resp2.read()
    return None


def display_thumbnail(filename, label="", ascii_width=50):
    """Display a thumbnail in the terminal."""
    print()
    print(f"  {label}")
    
    img_data = download_thumbnail(filename, width=200)
    if not img_data:
        print(f"  [Could not download thumbnail for {filename[:50]}]")
        return
    
    ascii_text = ascii_art(img_data, ascii_width=ascii_width)
    if ascii_text:
        print(ascii_text)
    else:
        print(f"  [Rendering failed for {filename[:50]}]")


if __name__ == '__main__':
    # Quick test
    display_thumbnail("Apples_with_black_background.jpg", "Test")
