"""
Top Commons - Organic Interest Ranking

Ranks images by a composite score that measures genuine organic interest
rather than structural/infrastructure-driven traffic.

Scoring:
  1. Base: filter out known utility/noise images (extension + blocklist)
  2. Fetch global page usage count for each remaining image
  3. Organic Score = total_requests / max(1, global_usage_count)
     - Higher = more interest per page where it appears
     - Very high = direct hotlinking or specific image interest
  4. Also compute: template_usage_score, spike_readiness (day-over-day)
"""
import json, sys, re, urllib.parse, subprocess, time

# ─── CONFIG ────────────────────────────────────────────────────
HEADERS = ['-H', 'User-Agent: TopCommonsResearch/1.0 (alih@example.com)']
MONTHLY_URL = "https://wikimedia.org/api/rest_v1/metrics/mediarequests/top/all-referers/all-media-types/2026/05/all-days"
MAX_API_CALLS = 150  # don't burn too many API calls

# ─── UTILITY FILTER ────────────────────────────────────────────

def classify_image(f):
    """Returns 'substantive' or 'utility'."""
    path = f['file_path']
    if not path.startswith('/wikipedia/commons/'):
        return 'utility'
    parts = path.split('/')
    if len(parts) < 5:
        return 'utility'
    filename = urllib.parse.unquote(parts[-1])
    name_lower = filename.lower()
    name_no_ext = name_lower.rsplit('.', 1)[0]

    img_exts = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.webp')
    if not any(name_lower.endswith(e) for e in img_exts):
        return 'utility'

    # Blocklist
    utility_set = {
        'picto_infobox_military', 'picto_infobox_auteur', 'picto_infobox_masks',
        'picto_infobox_fotbal', 'picto_infobox_book', 'picto_infobox',
        'nuvola_apps_package_graphics', 'nuvola_apps_kaboodle',
        'nuvola_apps_edu_mathematics_blue-p', 'nuvola_france_flag',
        'nuvola_usa_flag', 'nuvola_lgbt_flag',
        'wikimedia-logo-blackandwhite', 'wikimedia-logo',
        'wikidata_favicon_color', 'wikidata_favicon', 'wikipedia-logo',
        'wikinews-logo', 'wikisource-logo', 'wikiversity_logo_2017',
        'wikifunctions-logo', 'commons-logo', 'wikivoyage-logo',
        'wikibooks_writing_contest',
        'closewindow19x19', 'closewindow', 'closewindow.png',
        'mediawiki_vector_skin_right_arrow.png', 'jump-to-top_icon',
        'transparent_square', 'transparent', 'blank_icon',
        'red_arrow_down', 'green_arrow_up', 'red_pog', 'blue_star_unboxed',
        'gthumb', 'speaker_icon', 'group_half', 'people_icon',
        'star_full', 'star_empty', 'star_half',
        'gold_medal_icon', 'silver_medal_icon', 'bronze_medal_icon',
        'silver_medal', 'gold_record_icon',
        'arrowleftnavbox', 'arrowrightnavbox',
        'disambig_grey', 'disambig_gray', 'disambig_gray_rtl',
        'information_icon', 'information_icon4', 'info_simple',
        'emblem-important', 'question_book', 'gtk-dialog-question',
        'incomplete_list', 'compositing',
        'feed-icon', 'oojs_ui_icon_alert-warning', 'oojs_ui_icon_notice-warning',
        'hecker_gnu_white', 'gnu_head',
        'cc-by_new_white', 'cc-sa', 'cc-zero',
        'balance,_by_david', 'balance, by david',
        'pictogram_voting_info',
        'icon_pdf_file', 'folder_hexagonal_icon',
        'camera-photo_upload',
        'edit-clear', 'tango-nosources', 'tango_style_wikipedia_icon',
        'broom_icon',
        'soccerball_shade', 'soccerball_shade_cross',
        'soccerball_shad_check', 'soccerball',
        'soccer', 'basketball_pictogram',
        'p_culture', 'p_sport', 'p_religion', 'p_history',
        'social_sciences', 'sciences_humaines',
        'sub_off', 'yellow_flag_waving', 'red_flag_ii',
        'blue_pog', 'green_pog',
        'bsicon_str',
        'left_pointing_double_angle_quotation_mark_sh1',
        'icons-mini-file_acrobat', 'icons-mini-file_acrobat.gif',
        'image-silk', 'information-silk',
        'bon_article', 'qsicon_exzellent', 'qsicon_lesenswert',
        'test_template_info-icon_-_version_(2)',
        'w3c_grn', 'global_thinking',
        'intellectual_property_noun_project',
        'up_(89591)_-_the_noun_project',
        'wikipedia_african_month_logo',
        'wle_austria_logo_(text_right)', 'wle_germany_banner_2023',
        'hs_vdq', 'hsdagensdatum',
        'wma_button2b', 'wp25_primary_lockup_white_25',
        'discord_color_d', 'wikipedia25-bus_grafik',
        'translate_link_color_crop',
        'bangla_wikiconnect_logo_-_bn',
        'numeral_converter_icon_1',
        'decrease_neutral', 'increase_neutral',
        'industry5', 'pl_wiki_aktualnosci_ikona',
        'example_of_the_brenizer_method',
        'nbsfirstscanimagerestored',
        'png_transparency_demonstration_1',
        'earth-moon',
        'dotxxx', 'images', 'terra', 'socrates',
        'pierrelune', 'empty', 'empty.png',
        'telegram_messenger', 'whatsapp_icon', 'sports_icon', 'instagram_icon',
        'audio-input-microphone', 'png_test',
        'aviacionavion',
        'wikilovespride_2026_elementos-10',
        'wikilovespride_2026_elementos_derivado_barba_editor_lgbt',
        'banner_2_1200', 'banner_2_320',
        'pressefotocp_2',
        'wikipedia-tagline-de-25',
        'get_it_on_f-droid', 'download_on_the_app_store_badge',
        'nissan_2020_logo', 'abc-2021-logo',
        'mplayer', 'mplayer.svg',
        'google_favicon_2025', 'google_favicon',
        'facebook_f_logo_(2019)', 'x_logo_2023_original',
        'notification-icon-wikivoyage-logo',
        'trademark_warning_symbol',
        'gtk-dialog-info-14px',
        'treeview-grey-line',
        'cscr-featured', 'cscr-featured.png',
        'logo_original-t',
        'mbc1logo',
        'logo_television_blanc',
        'emblema_de_atenção_às_lacunas',
        'adults_only_warning',
        'wlbangla2026_rolling_banner',
        'blue_ipod_nano', 'blue_ipod_nano.jpg',
        'valeriana_officinalis_inflorescence_-_niitvälja',
        'black_arrow_down',
        'red_arrow_up',
        'copyrightpirates',
        'megaphone_icon',
    }
    if name_no_ext in utility_set:
        return 'utility'

    utility_pats = [
        r'^flag_of_', r'^flag_of_the_',
        r'_logo\.', r'_logo_',
        r'favicon',
        r'get_it_on_', r'download_on_the_',
        r'google_play|app_store',
        r'seal_of_',
        r'location_map|orthographic_projection|blank_map',
        r'userbox|sf-userbox',
        r'kit_body|kit_shorts|kit_socks|kit_left_arm|kit_right_arm',
        r'banner_\d+x?\d*\.png',
        r'facebook.*logo|twitter.*logo|instagram.*logo',
        r'youtube.*logo|netflix.*logo',
        r'discord.*logo|telegram.*logo',
        r'google.*logo|apple.*logo|mastercard',
        r'nissan.*logo|abc-2021|line_logo',
        r'bein_sport|dsports\.png|a24_',
        r'world_map_fifa',
        r'animated-flag-',
        r'vampire_smiley',
        r'red_pog|picto_infobox|nuvola_',
        r'closewindow|openwindow',
        r'cc-by|cc-sa|hecker_gnu|gnu_head',
        r'arrowleftnavbox|arrowrightnavbox',
        r'arrow_up|arrow_down|arrow_left|arrow_right',
        r'star_full|star_empty|star_half',
        r'gold_medal|silver_medal|bronze_medal',
        r'disambig_grey|disambig_gray',
        r'information_icon|info_simple|info_icon|info_silk',
        r'question_book|gtk-dialog-question',
        r'incomplete_list|compositing',
        r'tango-nosources|tango_style',
        r'feed-icon|oojs_ui|emoji',
        r'soccerball|basketball_pictogram',
        r'p_culture|p_sport|p_history|p_religion|p_social',
        r'social_sciences|sciences_humaines',
        r'image-silk|information-silk',
        r'group_half|people_icon',
        r'pictogram_voting',
        r'transparent_square\.png',
        r'jump-to-top',
        r'balance,_by_david|balance, by david',
        r'mediawiki_vector_skin',
        r'gthumb',
        r'speaker_icon',
        r'camera-photo_upload',
        r'broom_icon',
        r'sub_off',
        r'yellow_flag_waving|red_flag_ii',
        r'blue_star_unboxed',
        r'bsicon_',
        r'left_pointing_double_angle_quotation_mark',
        r'w3c_grn',
        r'intellectual_property_noun',
        r'wle_austria|wle_germany',
        r'hs_vdq|hsdagensdatum',
        r'wma_button|wp25_',
        r'decrease_neutral|increase_neutral',
        r'example_of_the_brenizer|nbsfirstscanimage|numeral_converter',
        r'png_transparency_demo|earth-moon',
        r'dotxxx|^images\.|terra\.png|socrates\.png|pierrelune',
        r'empty\.png|png_test',
        r'audio-input-microphone',
        r'^wp_|^wikipedia-tagline',
        r'wikilovespride.*elementos',
        r'global_thinking\.svg|wikidata_favicon|wikibooks_writing_contest',
        r'wikimedia-logo|wikipedia-logo\.png|commons-logo',
        r'wikiversit|wikinews|wikisource|wikifunctions|wikivoyage|wikidata',
        r'mplayer\.svg|google_favicon|facebook_f_logo|x_logo_2023',
        r'notification-icon|trademark_warning_symbol',
        r'pl_wiki_aktualnosci|industry5\.svg|up_\(89591\)',
        r'pictogram_voting|folder_hexagonal|icon_pdf|camera-photo',
        r'edit-clear|compositing',
        r'telegram_messenger|whatsapp_icon|sports_icon|instagram_icon',
        r'wikilovespride|pressefotocp|wle_|hs_|wp25_|wma_button',
        r'wikipedi._african_month|bon_article|qsicon_|test_template',
        r'nissan_2020|abc-2021|line_logo',
        r'get_it_on|download_on_the|google_play_badge|app_store_badge',
        r'global_thinking|bangla_wikiconnect|translate_link_color',
        r'numeral_converter|decrease_neutral|increase_neutral|pl_wiki',
        r'w3c_grn|yelp_logo|dotxxx|^images\.png',
        r'kh_|ks_|kra_|kta_|kis_',  # kit parts
        r'^tux\.|^gnu_',
        r'hyperlink|_icon\.',
        r'button_|_button\.',
        r'wiktionary-logo',
        r'metallica',
        r'gtk-dialog',
        r'treeview-.*-line',
        r'cscr-featured',
        r'logo_original',
        r'^mbc.*logo',
        r'logo_television',
        r'emblema_de_aten',
        r'adults_only_warning',
        r'wlbangla.*banner',
        r'blue_ipod',
        r'copyrightpirate',
        r'iphone\d+white',
        r'pepsi_355_ml',
        r'coin_of_',
        r'^logo',
    ]
    for pat in utility_pats:
        if re.search(pat, name_lower):
            return 'utility'
    return 'substantive'

# ─── API HELPERS ───────────────────────────────────────────────

def curl(url):
    result = subprocess.run(
        ['curl', '-s', url] + HEADERS,
        capture_output=True, text=True, timeout=20
    )
    return result.stdout

def get_global_usage(filename):
    """Returns (usage_count, has_more, namespace_counts)."""
    encoded = urllib.parse.quote(filename)
    url = (f"https://commons.wikimedia.org/w/api.php"
           f"?action=query&format=json&prop=globalusage"
           f"&titles=File:{encoded}&gulimit=500&guprop=namespace|pageid|url")
    data = json.loads(curl(url))
    pages = data.get('query', {}).get('pages', {})
    has_more = 'gucontinue' in data.get('continue', {})
    usages = []
    for pid, pdata in pages.items():
        if 'globalusage' in pdata:
            usages.extend(pdata['globalusage'])
    ns_counts = {}
    article_count = 0
    template_count = 0
    module_count = 0
    user_count = 0
    for u in usages:
        ns = int(u.get('ns', -1))
        ns_counts[ns] = ns_counts.get(ns, 0) + 1
        if ns == 0:
            article_count += 1
        elif ns in (10, 828):
            template_count += 1
            if ns == 828:
                module_count += 1
        elif ns in (2, 3):
            user_count += 1
    return len(usages), has_more, ns_counts, article_count, template_count, module_count, user_count

# ─── MAIN ──────────────────────────────────────────────────────

print("Fetching monthly mediarequests top 1000...")
data = json.loads(curl(MONTHLY_URL))
all_files = data['items'][0]['files']
print(f"  Got {len(all_files)} files")

# Filter to substantive
substantive = [f for f in all_files if classify_image(f) == 'substantive']
print(f"  Substantive images: {len(substantive)}")
print(f"  Fetching global usage data...")

# Fetch usage counts
results = []
for i, f in enumerate(substantive):
    if i >= MAX_API_CALLS:
        print(f"  Hit API call limit ({MAX_API_CALLS}), stopping...")
        break
    
    filename = urllib.parse.unquote(f['file_path'].split('/')[-1])
    usage_count, has_more, ns_counts, article_count, template_count, module_count, user_count = get_global_usage(filename)
    
    total_reqs = f['requests']
    organic_score = total_reqs / max(1, usage_count)
    
    results.append({
        'filename': filename,
        'file_path': f['file_path'],
        'requests': total_reqs,
        'overall_rank': f['rank'],
        'usage_count': usage_count,
        'usage_has_more': has_more,
        'article_count': article_count,
        'template_count': template_count,
        'module_count': module_count,
        'user_count': user_count,
        'ns_counts': ns_counts,
        'organic_score': organic_score,
    })
    
    if (i + 1) % 20 == 0:
        print(f"  ... {i+1}/{len(substantive)} processed")
    
    time.sleep(0.15)  # Rate limiting

print(f"\nProcessed {len(results)} images\n")

# Sort by organic score (descending)
results.sort(key=lambda r: -r['organic_score'])

# ─── OUTPUT ────────────────────────────────────────────────────

print("=" * 120)
print("TOP 50 — ORGANIC INTEREST RANKING (May 2026)")
print("Ranked by: requests per wiki usage (higher = more organic interest per page)")
print("=" * 120)
print(f"{'Rk':>3s} {'Prev':>4s} {'Reqs/mo':>12s} {'CScore':>10s} {'WikiUses':>8s} {'Arts':>4s} {'Templ':>4s} {'User':>4s}  Image")
print("-" * 120)

for i, r in enumerate(results[:50], 1):
    fn = r['filename']
    if len(fn) > 55:
        fn = fn[:52] + '...'
    has_more_str = "+" if r['usage_has_more'] else " "
    organic_str = f"{r['organic_score']:,.0f}"
    print(f"{i:3d}  #{r['overall_rank']:3d}{has_more_str}  {r['requests']:>10,}  {organic_str:>10s}  {r['usage_count']:>4d}{has_more_str:>4s}  {r['article_count']:>3d}  {r['template_count']:>3d}  {r['user_count']:>3d}  {fn}")

print()

# Show the "always on top" evergreen images for comparison
print("=" * 120)
print("EVERGREEN IMAGES (high total traffic, low organic score — structural)")
print("=" * 120)
evergreens = [r for r in results if r['organic_score'] < 150000 and r['usage_count'] >= 200]
evergreens.sort(key=lambda r: -r['requests'])
for i, r in enumerate(evergreens[:8], 1):
    fn = r['filename']
    if len(fn) > 50:
        fn = fn[:47] + '...'
    has_more_str = "+" if r['usage_has_more'] else " "
    print(f"  {r['requests']:>10,}/mo  {r['organic_score']:>8,.0f} req/usage  {r['usage_count']:>3d}{has_more_str} wiki uses  {fn}")

print()

# Orphan images (zero wiki usage)
print("=" * 120)
print("ORPHAN IMAGES (zero wiki usage — all traffic from external/direct sources)")
print("=" * 120)
orphans = [r for r in results if r['usage_count'] == 0]
for r in orphans:
    fn = r['filename']
    if len(fn) > 60:
        fn = fn[:57] + '...'
    print(f"  #{r['overall_rank']:>4d}  {r['requests']:>10,}/mo  {fn}")
if not orphans:
    print("  (none found in this batch)")
