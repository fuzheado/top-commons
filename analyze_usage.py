"""Analyze global usage patterns for specific Commons images."""
import json, sys, urllib.parse, subprocess, re

test_images = [
    ("Cat03.jpg", "62M/mo", "#93 overall"),
    ("Crab_Nebula.jpg", "6.2M/mo", "#763"),
    ("Flag_of_Italy.svg", "117M/mo", "#35 overall - utility"),
    ("Commons-logo.svg", "461M/mo", "#1 overall - utility"),
    ("Red_pog.svg", "186M/mo", "#22 overall - utility"),
    ("Ebola_Virus_-_Electron_Micrograph.tiff", "10.2M/mo", "substantive"),
    ("StalinCropped1943.jpg", "4.6M/mo", "substantive"),
    ("Info_Simple.svg", "126M/mo", "#33 overall - utility"),
    ("Icon_pdf_file.png", "259M/mo", "#16 overall - utility"),
    ("Gigantic_jet_NOIRLab.jpg", "10M/mo", "substantive"),
    ("Apples_with_black_background.jpg", "17M/mo", "substantive - 0 wiki usages!"),
    ("Foodiesfeed.com_pouring-honey-on-pancakes-with-walnuts.jpg", "10M/mo", "substantive"),
    ("Killerwhales_jumping.jpg", "6M/mo", "substantive"),
    ("The_Kelpies_at_The_Helix_in_Falkirk,_Scotland,_June_2014.jpg", "7M/mo", "substantive"),
    ("Hollywood_Sign_(Zuschnitt).jpg", "5.9M/mo", "substantive"),
    ("Hitler_portrait_crop_(cropped)(2).jpg", "7.8M/mo", "substantive"),
    ("Saint_Peter's_Basilica_facade,_Rome,_Italy.jpg", "6.1M/mo", "substantive"),
    ("Blue_star_unboxed.svg", "5.8M/mo", "#818 overall - utility SVG"),
    ("ArrowRightNavbox.svg", "12M/mo", "#436 - utility"),
]

NAMESPACE_LABELS = {
    0: "Main/Article", 1: "Talk", 2: "User", 3: "User_talk",
    4: "Project", 5: "Project_talk", 6: "File", 7: "File_talk",
    8: "MediaWiki", 10: "Template", 11: "Template_talk",
    14: "Category", 828: "Module",
}

def get_global_usage(filename):
    """Get global usage for a file. Returns list of usage dicts."""
    encoded = urllib.parse.quote(filename)
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=globalusage&titles=File:{encoded}&gulimit=500&guprop=namespace|pageid|url"
    
    result = subprocess.run(
        ["curl", "-s", url, "-H", "User-Agent: TopCommonsResearch/1.0 (alih@example.com)"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    
    pages = data.get('query', {}).get('pages', {})
    has_more = 'continue' in data and 'gucontinue' in data.get('continue', {})
    
    usages = []
    for pid, pdata in pages.items():
        if 'globalusage' in pdata:
            usages.extend(pdata['globalusage'])
    
    return usages, has_more

def get_commons_fileusage(filename):
    """Get file usage on Commons itself."""
    encoded = urllib.parse.quote(filename)
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=fileusage&titles=File:{encoded}&fulimit=500"
    
    result = subprocess.run(
        ["curl", "-s", url, "-H", "User-Agent: TopCommonsResearch/1.0 (alih@example.com)"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    
    pages = data.get('query', {}).get('pages', {})
    usages = []
    for pid, pdata in pages.items():
        if 'fileusage' in pdata:
            usages.extend(pdata['fileusage'])
    
    return usages

def ns_name(ns):
    return NAMESPACE_LABELS.get(ns, f"NS{ns}")

print(f"{'IMAGE':55s} {'REQS':>10s} {'GLOBAL':>6s} {'CMONS':>6s} {'TEMPL':>5s} {'MAIN':>5s} {'USER':>5s} {'OTHER':>5s}  RATIO")
print("=" * 110)

for img_name, reqs, note in test_images:
    usages, has_more = get_global_usage(img_name)
    commons_usage = get_commons_fileusage(img_name)
    
    total_global = len(usages)
    more_str = "+" if has_more else ""
    total_commons = len(commons_usage)
    
    # Namespace breakdown
    ns_counts = {}
    for u in usages:
        ns = int(u.get('ns', -1))  # 'ns' is a string like '0'
        ns_counts[ns] = ns_counts.get(ns, 0) + 1
    
    in_templates = ns_counts.get(10, 0) + ns_counts.get(828, 0)
    in_main = ns_counts.get(0, 0)
    in_user = ns_counts.get(2, 0) + ns_counts.get(3, 0)
    other = total_global - in_templates - in_main - in_user
    
    # Compute a "structural score"
    # If >50% of usage is in templates or it has 500+ uses → structural
    if total_global > 0:
        template_pct = in_templates / total_global * 100
        structural = "STRUCTURAL" if (template_pct > 50 or total_global >= 500) else "organic"
    else:
        template_pct = 0
        structural = "NO-WIKI-USE"
    
    # Ratio: requests per usage page (higher = more organic per-page interest)
    # Extract numeric requests
    reqs_num = int(re.sub(r'[^0-9]', '', reqs.split('/')[0])) * 1000000 if 'M' in reqs.split('/')[0] else int(re.sub(r'[^0-9]', '', reqs.split('/')[0]))
    
    if total_global > 0:
        ratio = f"{reqs_num // max(total_global, 1):>6,}"
    else:
        ratio = "   INF"
    
    display_name = img_name[:53] + ".." if len(img_name) > 55 else img_name
    print(f"{display_name:55s} {reqs:>10s} {total_global:>3d}{more_str:>3s} {total_commons:>5d}  {in_templates:>4d} {in_main:>4d} {in_user:>4d} {other:>4d}  {ratio:>6s}  [{structural}]")
    
    # Show NS breakdown details for interesting cases
    if total_global > 0 and total_global < 500:
        detail = ", ".join(f"{ns_name(ns)}:{c}" for ns, c in sorted(ns_counts.items(), key=lambda x: -x[1])[:5])
        print(f"  └── {detail}")
    elif total_global >= 500:
        detail = ", ".join(f"{ns_name(ns)}:{c}" for ns, c in sorted(ns_counts.items(), key=lambda x: -x[1])[:5])
        print(f"  └── {detail} (first 500)")
    print()
