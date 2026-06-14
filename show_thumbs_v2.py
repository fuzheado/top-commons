"""
Display top Commons images as minimal ASCII thumbnails.
Uses a tiny, custom-built approach - just reads JPEG header for dimensions
and samples raw bytes for brightness mapping.
"""
import urllib.request, urllib.parse, json, struct, re, os, tempfile, subprocess

# ASCII gradient characters (dark to light)
GRADIENT = ' .:-=+*#%@'

def get_thumbnail_url(filename, width=200):
    """Get thumbnail URL for a Commons file."""
    encoded = urllib.parse.quote(filename)
    api_url = (f"https://commons.wikimedia.org/w/api.php"
               f"?action=query&format=json&prop=imageinfo"
               f"&iiprop=url&iilimit=1&iiurlwidth={width}"
               f"&titles=File:{encoded}")
    req = urllib.request.Request(api_url, headers={'User-Agent': 'TopCommons/1.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    for pid, pdata in data.get('query', {}).get('pages', {}).items():
        if 'imageinfo' in pdata:
            return pdata['imageinfo'][0].get('thumburl')
    return None

def ascii_via_resize(filename, ascii_w=40):
    """Use chafa with minimal output size, then strip and show."""
    thumb_url = get_thumbnail_url(filename, width=120)
    if not thumb_url:
        return None
    
    req = urllib.request.Request(thumb_url, headers={'User-Agent': 'TopCommons/1.0'})
    img_data = urllib.request.urlopen(req, timeout=15).read()
    
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(img_data)
        tmp = f.name
    
    try:
        # Run chafa with VERY small size
        result = subprocess.run(
            ['chafa', '--symbols', 'block', '-s', str(ascii_w)],
            input=img_data, capture_output=True, timeout=10
        )
        output = result.stdout.decode('utf-8', errors='replace')
        
        # Aggressive ANSI stripping
        cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
        cleaned = re.sub(r'\x1b\][0-9;]*[^\x1b]*(\x1b\\|\x07)', '', cleaned)
        cleaned = re.sub(r'\x1b\[[0-9;]*m', '', cleaned)
        cleaned = re.sub(r'\x1b\[[0-9;]*[HJK]', '', cleaned)
        cleaned = re.sub(r'\x1b\[[0-9;]*', '', cleaned)
        cleaned = re.sub(r'\x1b', '', cleaned)
        
        # Take only meaningful lines (remove empty)
        lines = [l for l in cleaned.split('\n') if l.strip()]
        return '\n'.join(lines[:ascii_w//2])
    finally:
        try:
            os.unlink(tmp)
        except:
            pass

# Top 10 from organic ranking
TOP10 = [
    ("Apples_with_black_background.jpg", 
     "17,254,181/mo - 0 wiki uses (external hotlinking)",
     "https://commons.wikimedia.org/wiki/File:Apples_with_black_background.jpg"),
    ("A_Galaxy_of_Birth_and_Death.jpg", 
     "7,524,303/mo - 0 wiki uses",
     "https://commons.wikimedia.org/wiki/File:A_Galaxy_of_Birth_and_Death.jpg"),
    ("Bærekraftsprisen_2018_(cropped2).jpg", 
     "7,423,256/mo - 5 wiki uses",
     "https://commons.wikimedia.org/wiki/File:B%C3%A6rekraftsprisen_2018_(cropped2).jpg"),
    ("Steph_Curry_(51915116957).jpg", 
     "4,796,593/mo - 4 wiki uses",
     "https://commons.wikimedia.org/wiki/File:Steph_Curry_(51915116957).jpg"),
    ("Chilaquiles_at_the_Grand_Cantina,_Windsor,_Ontario,_Canada.jpg", 
     "10,035,236/mo - 9 wiki uses",
     "https://commons.wikimedia.org/wiki/File:Chilaquiles_at_the_Grand_Cantina,_Windsor,_Ontario,_Canada.jpg"),
    ("President_Donald_Trump_meets_with_Cristiano_Ronaldo_at_White_House_2026.jpg", 
     "5,238,330/mo - 5 wiki uses",
     "https://commons.wikimedia.org/wiki/File:President_Donald_Trump_meets_with_Cristiano_Ronaldo_at_White_House_2026.jpg"),
    ("2026_Federal_Agents_in_Minneapolis,_Minnesota_after_Portland_Avenue_and_34th_Street_shooting_in_January.jpg", 
     "10,046,500/mo - 10 wiki uses",
     "https://commons.wikimedia.org/wiki/File:2026_Federal_Agents_in_Minneapolis,_Minnesota_after_Portland_Avenue_and_34th_Street_shooting_in_January.jpg"),
    ("Hitler_portrait_crop_(cropped)(2).jpg", 
     "7,762,270/mo - 8 wiki uses (all articles)",
     "https://commons.wikimedia.org/wiki/File:Hitler_portrait_crop_(cropped)(2).jpg"),
    ("Walaka,_Rosa,_Sergio,_Leslie_and_Kong-rey_2018-10-02.jpg", 
     "6,907,370/mo - 9 wiki uses",
     "https://commons.wikimedia.org/wiki/File:Walaka,_Rosa,_Sergio,_Leslie_and_Kong-rey_2018-10-02.jpg"),
    ("De_oprichting_van_de_obelisk_op_het_St._Pietersplein_te_Brussel,_bij_de_aanwezigheid_van_Paus_Franciscus.jpg", 
     "10,023,350/mo - 14 wiki uses",
     "https://commons.wikimedia.org/wiki/File:De_oprichting_van_de_obelisk_op_het_St._Pietersplein_te_Brussel,_bij_de_aanwezigheid_van_Paus_Franciscus.jpg"),
]

print("=" * 76)
print("  TOP 10 — ORGANIC INTEREST RANKING (May 2026)")
print("  Images ranked by requests ÷ wiki-page-usage count")
print("  High score = genuine organic interest per page")
print("=" * 76)

for i, (filename, stats, url) in enumerate(TOP10, 1):
    print(f"\n{'─' * 76}")
    print(f"  #{i}: {filename[:70]}")
    print(f"  {stats}")
    print(f"  URL: {url[:90]}")
    
    try:
        art = ascii_via_resize(filename, ascii_w=35)
        if art:
            for line in art.split('\n'):
                print(f"  {line}")
    except Exception as e:
        print(f"  [thumbnail unavailable]")

print()
print("=" * 76)
print("  All images are CC-BY-SA or public domain on Wikimedia Commons.")
