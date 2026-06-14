"""Show terminal thumbnails of the top 10 organic interest images."""
import json, subprocess, urllib.parse, sys, os, tempfile

# Top 10 from organic ranking (hardcoded from previous run)
TOP10 = [
    ("Apples_with_black_background.jpg", "17,254,181", "0 wiki uses — external hotlinking only"),
    ("A_Galaxy_of_Birth_and_Death.jpg", "7,524,303", "0 wiki uses — external hotlinking only"),
    ("Bærekraftsprisen_2018_(cropped2).jpg", "7,423,256", "5 wiki uses, 4 in articles"),
    ("Steph_Curry_(51915116957).jpg", "4,796,593", "4 wiki uses, 4 in articles"),
    ("Chilaquiles_at_the_Grand_Cantina,_Windsor,_Ontario,_Canada.jpg", "10,035,236", "9 wiki uses"),
    ("President_Donald_Trump_meets_with_Cristiano_Ronaldo_at_White_House_2026.jpg", "5,238,330", "5 wiki uses, all articles"),
    ("2026_Federal_Agents_in_Minneapolis,_Minnesota_after_Portland_Avenue_and_34th_Street_shooting_in_January.jpg", "10,046,500", "10 wiki uses"),
    ("Hitler_portrait_crop_(cropped)(2).jpg", "7,762,270", "8 wiki uses, all articles"),
    ("Walaka,_Rosa,_Sergio,_Leslie_and_Kong-rey_2018-10-02.jpg", "6,907,370", "9 wiki uses, 3 in articles"),
    ("De_oprichting_van_de_obelisk_op_het_St._Pietersplein_te_Brussel,_bij_de_aanwezigheid_van_Paus_Franciscus.jpg", "10,023,350", "14 wiki uses"),
]

def get_thumbnail_url(filename):
    """Get the thumbnail URL for a Commons file."""
    encoded = urllib.parse.quote(filename)
    url = (f"https://commons.wikimedia.org/w/api.php"
           f"?action=query&format=json&prop=imageinfo"
           f"&iiprop=url&iilimit=1&iiurlwidth=400"
           f"&titles=File:{encoded}")
    result = subprocess.run(
        ['curl', '-s', url, '-H', 'User-Agent: TopCommonsThumbs/1.0'],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    pages = data.get('query', {}).get('pages', {})
    for pid, pdata in pages.items():
        if 'imageinfo' in pdata:
            return pdata['imageinfo'][0].get('thumburl', pdata['imageinfo'][0].get('url'))
    return None

def display_image_with_chafa(image_data, label):
    """Display an image using chafa in the terminal."""
    # Write image data to temp file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(image_data)
        tmp_path = f.name
    
    try:
        # Use chafa to display
        result = subprocess.run(
            ['chafa', '--symbols', 'block', '-s', '60x20', '--color-space', 'rgb', tmp_path],
            capture_output=True, text=True, timeout=10
        )
        print(result.stdout)
        # Also print the text label below
        print(f"  {label}")
    finally:
        os.unlink(tmp_path)

print("=" * 80)
print("  TOP 10 — ORGANIC INTEREST IMAGES (May 2026)")
print("  Ranked by: requests per wiki usage")
print("  Higher score = more organic interest per page where it's used")
print("=" * 80)
print()

for i, (filename, reqs, note) in enumerate(TOP10, 1):
    print(f"─── #{i} — {'─' * 60}")
    print(f"  {filename}")
    print(f"  {reqs} requests/mo — {note}")
    
    thumb_url = get_thumbnail_url(filename)
    if thumb_url:
        try:
            result = subprocess.run(
                ['curl', '-s', thumb_url, '-H', 'User-Agent: TopCommonsThumbs/1.0'],
                capture_output=True, timeout=15
            )
            if result.stdout:
                display_image_with_chafa(result.stdout, f"  Rank #{i} | {reqs}/mo | Organic Score: {note.split(' — ')[1] if ' — ' in note else ''}")
        except Exception as e:
            print(f"  [Error displaying thumbnail: {e}]")
    else:
        print(f"  [Could not get thumbnail]")
    print()
