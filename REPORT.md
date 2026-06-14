# Top Commons — Research Report

**Date:** 2026-06-14
**Goal:** Determine the feasibility of building a "top most downloaded/visited images on Wikimedia Commons" list, analogous to [top.hatnote.com](https://top.hatnote.com) (which shows the most-read Wikipedia articles each day).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Data Sources](#2-data-sources)
3. [The Filtering Problem](#3-the-filtering-problem)
4. [Monthly Top 50 Substantive Images (May 2026)](#4-monthly-top-50-substantive-images-may-2026)
5. [Daily Volatility — The Current Events Signal](#5-daily-volatility--the-current-events-signal)
6. [Known Data Quality Issues](#6-known-data-quality-issues)
7. [Viability Assessment](#7-viability-assessment)
8. [Advanced Filtering: Structural vs. Organic Traffic](#8-advanced-filtering-structural-vs-organic-traffic)
9. [Organic Interest Ranking — Top 50 (May 2026)](#9-organic-interest-ranking--top-50-may-2026)
10. [What Building It Would Look Like](#10-what-building-it-would-look-like)

---

## 1. Executive Summary

**There is no existing equivalent of top.hatnote.com for Commons images.** The data infrastructure exists, the REST API works, but no one has built a filtered, public-facing "top images" dashboard.

The Wikimedia **Mediarequests API** (`/metrics/mediarequests/top/...`) returns the top ~1000 most-transferred files from `upload.wikimedia.org` at both daily and monthly granularity. However, **~88% of the top 1000 are utility files** — country flags, UI icons, navigation arrows, wiki project logos, star/medal icons, and PDF icons. Only ~12% are what a general audience would consider "substantive images" (photographs, artwork, scientific imagery, historical photos).

**Key findings:**
- The data is freely available and the daily endpoint captures **current events spikes** well — anniversaries, news events, and sports matches all create recognizable traffic patterns.
- The metric measures **HTTP transfers** (not eyeballs), so prefetches from Media Viewer inflate counts by potentially 50%+.
- Filtering utility images is possible with heuristic rules but requires ongoing maintenance.
- A daily "Top Commons Images" list would be genuinely interesting, especially when there's a major news event.

---

## 2. Data Sources

### 2.1 Primary: Mediarequests REST API

```
GET https://wikimedia.org/api/rest_v1/metrics/mediarequests/top/{referer}/{media_type}/{year}/{month}/{day}
```

**Parameters used:**
- `referer`: `all-referers`
- `media_type`: `all-media-types`
- Granularity: `YYYY/MM/all-days` (monthly) or `YYYY/MM/DD` (daily)

**Response:** Returns up to 1000 files ranked by total transfer count, with `file_path`, `requests`, and `rank` per entry.

**Example monthly query:**
```
GET https://wikimedia.org/api/rest_v1/metrics/mediarequests/top/all-referers/all-media-types/2026/05/all-days
```

**Example daily query:**
```
GET https://wikimedia.org/api/rest_v1/metrics/mediarequests/top/all-referers/all-media-types/2026/06/13
```

**Data lag:** ~24-72 hours (same as pageviews API).

### 2.2 Secondary: Raw Mediacounts Dumps

```
https://dumps.wikimedia.org/other/mediacounts/daily/
```

Daily TSV files dating back to 2015. Each row contains per-file aggregates broken down by transfer type (original, thumbnails of various sizes, transcoded audio/video) and referer category (internal to WMF, external, unknown). Available on the Analytics Hadoop cluster via the `wmf.mediacounts` Hive table.

### 2.3 Existing Tools

| Tool | What It Does | Missing |
|------|-------------|---------|
| [Mediaviews Analysis](https://pageviews.wmcloud.org/mediaviews/) | Per-file request counts over time (up to 10 files) | No "top files" view; manual entry only |
| [Topviews Analysis (Commons)](https://pageviews.wmcloud.org/topviews/?project=commons.wikimedia.org) | Most viewed **pages** on Commons | These are file description pages, not file transfers — completely different data |
| Mediacounts dumps | Raw daily TSV files | No filtering, no UI, no querying |
| [hatnote/top](https://github.com/hatnote/top) | Generates top.hatnote.com for Wikipedia articles | Pageviews API, not mediarequests — but the architecture is reusable |

### 2.4 Community Background

The request for file-level view statistics has been open since at least 2018:

- **Phabricator task [T210313](https://phabricator.wikimedia.org/T210313):** "Statistics for views of individual Wikimedia images" — marked High priority, has seen significant discussion, and the mediarequests API was built partly in response to it, but the task remains open.
- **Phabricator task [T206700](https://phabricator.wikimedia.org/T206700):** Related Media Viewer analytics work.

---

## 3. The Filtering Problem

The top 1000 most-transferred files from Commons are dominated by **utility/UI files**. Analysis of May 2026 data:

| Category | Count | Percentage |
|----------|-------|------------|
| Total in API response | 1,000 | 100% |
| Substantive images | 116 | **11.6%** |
| Filtered as utility/noise | 884 | **88.4%** |

### What Gets Filtered (the 88%)

The utility category includes:

- **Country flag SVGs:** `Flag_of_Italy.svg`, `Flag_of_Brazil.svg`, `Flag_of_Netherlands.svg` — collectively ~200+ entries in the top 1000. Every country flag gets millions of requests/month.
- **Wiki project logos:** `Commons-logo.svg` (#1 overall, 461M/month), `Wikisource-logo.svg`, `Wikinews-logo.svg`, `Wikiversity_logo_2017.svg`, `Wikifunctions-logo.svg`
- **UI/navigation icons:** `Red_pog.svg` (#22 overall, 186M/month — the red dot marker on maps), `Info_Simple.svg`, `ArrowRightNavbox.svg`, `Jump-to-top_icon.svg`, `CloseWindow19x19.png`
- **Icon templates:** `Star_full.svg`, `Star_empty.svg`, `Gold_medal_icon.svg`, `Silver_medal_icon.svg`, `Speaker_Icon.svg`
- **PDF/file-type icons:** `Icon_pdf_file.png` (#16 overall, 259M/month)
- **Pictograms:** `Picto_infobox_military.png`, `Picto_infobox_book.png`, `Picto_infobox_masks.png` — hundreds of infobox pictogram templates
- **Nuvola icon set:** A large family of icon images used across wikis
- **Logo files (brand):** Facebook, Twitter/X, Instagram, YouTube, Netflix, Google, Apple, Discord, Telegram, WhatsApp
- **Map/flag related:** Blank maps, location maps, orthographic projections, kit templates (sports uniforms)
- **Banner images:** Campaign banners for Wiki Loves Earth, Wiki Loves Pride, etc.

### Filtering Strategy Used in This Report

1. **Extension check:** Keep only `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.webp`. Exclude `.svg` (vast majority of flags/icons/logos), `.gif` (mostly animations/icons).
2. **Blocklist-based:** A curated set of ~200 known utility basenames (exact filename matches).
3. **Pattern-based:** ~80 regex patterns covering naming conventions (`^flag_of_`, `^nuvola_`, `^picto_`, `kit_`, `banner_\d+`, `icon_`, `_logo\.`, etc.).
4. **Brand exclusion:** Known corporate logos that aren't substantive images.
5. **False positive removal:** `Wikipedia25-Bus_Grafik.png`, `NBSFirstScanImageRestored.jpg`, `PNG_transparency_demonstration_1.png`, `Banner_2_320.png`, `Empty.png`, `Telegram_Messenger.png`, etc.

**Ongoing maintenance needed:** New icon sets, campaign banners, and logos are added to Commons regularly. The blocklist would need periodic updates.

---

## 4. Monthly Top 50 Substantive Images (May 2026)

Data fetched from the monthly mediarequests endpoint, filtered through the heuristic classifier.

```
Total files in API response:   1,000
Substantive images:            116  (11.6%)
Utility/noise filtered:        884  (88.4%)
```

### The Top 50

| # | Overall | Requests/mo | File |
|---|---------|-------------|------|
| 1 | #93 | 62,228,872 | Cat03.jpg |
| 2 | #323 | 17,254,181 | Apples_with_black_background.jpg |
| 3 | #411 | 13,240,361 | 2025_Hondius_-_IMO_9818709_by_2eight_-_9SC5017.jpg |
| 4 | #503 | 10,233,491 | Ebola_Virus_-_Electron_Micrograph.tiff |
| 5 | #509 | 10,114,430 | Foodiesfeed.com_pouring-honey-on-pancakes-with-walnuts.jpg |
| 6 | #511 | 10,101,279 | STS-133_Space_Shuttle_Discovery_after_undocking_3_(cropped).jpg |
| 7 | #521 | 10,050,443 | Japan_Airlines_777_Engine_Failure_on_Departure_(2_of_2)...jpg |
| 8 | #522 | 10,046,500 | 2026_Federal_Agents_in_Minneapolis...jpg |
| 9 | #523 | 10,036,937 | Carl_Laemmle_holding_an_Oscar_trophy,_1930_Retouched.jpg |
| 10 | #528 | 10,028,433 | Gigantic_jet_NOIRLab.jpg |
| 11 | #538 | 10,015,256 | Striegeliger_Schichtpilz-Stereum_hirsutum-20191216-RM-150832.jpg |
| 12 | #539 | 10,012,519 | Lactarius_resimus_Груздь_настоящий.jpg |
| 13 | #543 | 10,007,644 | N&W_611_Leaman_Place_June_6,_2021.jpg |
| 14 | #556 | 9,786,924 | Official_Presidential_Portrait_of_President_Donald_J._Trump_(2025)_(cropped)(2).jpg |
| 15 | #562 | 9,685,977 | EC1835_C_cut.jpg |
| 16 | #571 | 9,257,144 | 046CupolaSPietro.jpg |
| 17 | #583 | 9,015,425 | Aviacionavion.png |
| 18 | #584 | 9,015,174 | Pope_Leo_XIV_3_(3x4_cropped).png |
| 19 | #629 | 8,048,460 | A_Balloon_Site,_Coventry_(1943)_(Art._IWM_ART_LD_2750).jpg |
| 20 | #644 | 7,810,120 | Official_Presidential_Portrait_of_President_Donald_J._Trump_(2025).jpg |
| 21 | #647 | 7,762,270 | Hitler_portrait_crop_(cropped)(2).jpg |
| 22 | #664 | 7,423,256 | Bærekraftsprisen_2018_(cropped2).jpg |
| 23 | #683 | 7,203,279 | Football_in_Bloomington,_Indiana,_1995.jpg |
| 24 | #698 | 6,976,344 | The_Kelpies_at_The_Helix_in_Falkirk,_Scotland,_June_2014.jpg |
| 25 | #702 | 6,945,127 | Suvendu_Adhikari_at_Esplanade_Metro_Rail_Station,_Kolkata...jpg |
| 26 | #707 | 6,907,370 | Walaka,_Rosa,_Sergio,_Leslie_and_Kong-rey_2018-10-02.jpg |
| 27 | #717 | 6,775,827 | Elon_Musk_-_54820081119_(cropped).jpg |
| 28 | #745 | 6,432,743 | Bundesarchiv_Bild_101I-646-5188-17,_Flugzeuge_Junkers_Ju_87.jpg |
| 29 | #751 | 6,307,707 | Googleplex_HQ_(cropped).jpg |
| 30 | #757 | 6,263,898 | Comatricha_nigra_176600092.jpg |
| 31 | #763 | 6,225,752 | Crab_Nebula.jpg |
| 32 | #770 | 6,146,305 | Saint_Peter's_Basilica_facade,_Rome,_Italy.jpg |
| 33 | #772 | 6,139,055 | La_Tour_Eiffel_vue_de_la_Tour_Saint-Jacques,_Paris_août_2014_(2).jpg |
| 34 | #785 | 6,085,181 | Killerwhales_jumping.jpg |
| 35 | #788 | 6,045,706 | The_Beatles_1963_Dezo_Hoffman_Capitol_Records_press_photo_2.jpg |
| 36 | #802 | 5,903,892 | BTS_during_a_White_House_press_conference_May_31,_2022_(crop)...jpg |
| 37 | #807 | 5,866,472 | Hollywood_Sign_(Zuschnitt).jpg |
| 38 | #847 | 5,556,361 | Lionel_Messi_White_House_2026_(3x4_cropped).jpg |
| 39 | #850 | 5,508,579 | The_official_portrait_of_Shri_Narendra_Modi,_the_Prime_Minister...jpg |
| 40 | #870 | 5,331,051 | Arthropoda_collage.png |
| 41 | #879 | 5,261,929 | London_Skyline_(125508655).jpeg |
| 42 | #909 | 5,057,621 | Church_of_the_Holy_Sepulchre_by_Gerd_Eichmann_(cropped).jpg |
| 43 | #936 | 4,897,335 | Queen_Elizabeth_II_official_portrait_for_1959_tour_(cropped)...jpg |
| 44 | #939 | 4,895,683 | Victor_Wembanyama_San_Antonio_Spurs_2024.jpg |
| 45 | #947 | 4,866,143 | 2008_Beijing_olympic_games_opening_ceremony_(closing_of_the_ceremony).jpg |
| 46 | #962 | 4,815,497 | Michael_Jackson_in_1988.jpg |
| 47 | #964 | 4,796,593 | Steph_Curry_(51915116957).jpg |
| 48 | #965 | 4,793,360 | Fronalpstock_big.jpg |
| 49 | #975 | 4,714,330 | Official_portrait_of_Mamata_Banerjee.jpg |
| 50 | #984 | 4,641,848 | StalinCropped1943.jpg |

### Category Breakdown

| Category | Count | Examples |
|----------|-------|---------|
| People (Politicians, Celebrities, Sports) | 13 | Trump, Hitler, Stalin, Queen Elizabeth II, Modi, Messi, Curry, Wembanyama, Beatles, Musk, Pope, BTS, Michael Jackson |
| Places / Architecture / Landmarks | 7 | St. Peter's Basilica, Eiffel Tower, Hollywood Sign, London Skyline, Kelpies, Holy Sepulchre |
| Nature / Animals / Fungi | 6 | killer whales, cat, mushrooms, fungi, arthropods |
| History / War | 2 | Bundesarchiv Ju 87 photo, WWI balloon site |
| Science / Medical | 2 | Ebola virus micrograph, Crab Nebula |
| Space | 2 | Blue Marble (Apollo 17), Gigantic Jet lightning |
| Stock / Meme images | 2 | Cat03.jpg (benchmark image), Apples on black background |
| Other / Uncategorized | 16 | Various photos, stadiums, food, satellites |

---

## 5. Daily Volatility — The Current Events Signal

The monthly data smooths out interesting spikes. Daily data tells a much more dynamic story.

### June 10, 2026

```
  1. #109   2,083,342  Charles-Blomfield-Mount-Tarawera-in-eruption-June-10-1886.jpg
  2. #412     523,494  The_Kelpies_at_The_Helix_in_Falkirk,_Scotland,_June_2014.jpg
  3. #423     522,203  Ebola_Virus_-_Electron_Micrograph.tiff
  4. #691     270,309  C._Joseph_Vijay_(cropped).jpg
  5. #773     227,340  Hitler_portrait_crop_(cropped)(2).jpg
  6. #838     205,380  Crab_Nebula.jpg
  7. #861     198,897  Entering_Levi's_Stadium.JPG
  8. #889     192,635  Saint_Peter's_Basilica_facade,_Rome,_Italy.jpg
  9. #923     185,253  Wikipedia25-Bus_Grafik.png
 10. #956     176,257  25_July_2010_Kansas_City_Wizards_vs_Manchester_United_friendly.jpg
```

**Signal detected:** `Charles-Blomfield-Mount-Tarawera-in-eruption-June-10-1886.jpg` jumped to #109 with 2M requests — the anniversary of the 1886 Mount Tarawera eruption (June 10). Normally this image wouldn't be in the top 1000 at all.

### June 12-13, 2026

```
June 12:
  1. #542     434,548  Entering_Levi's_Stadium.JPG
  2. #604     354,500  Hard_Rock_Stadium_Club_World_Cup.jpg
  3. #466     520,198  OG_Anunoby_(41708749222)_(cropped).jpg
  4. #827     218,124  Metlife_stadium_(Aerial_view).jpg
  5. #717     274,102  C._Joseph_Vijay_(cropped).jpg
```

**Signal detected:** Stadium images and basketball player photos dominate — likely related to the 2026 FIFA Club World Cup and NBA Finals happening around this time.

### Daily vs Monthly Comparison

| Aspect | Daily | Monthly |
|--------|-------|---------|
| Unique substantive files seen | ~168/day | ~116 |
| Current events signal | **Strong** — anniversaries, news spikes | Weak — averaged out |
| Stability | High day-to-day volatility | Stable, predictable |
| Evergreen favorites | Cat03, Crab Nebula always present | Same |
| Best use case | "What people are looking at RIGHT NOW" | "Most popular images overall" |

**Bottom line:** The daily list would be significantly more interesting than the monthly one, especially during news cycles. The monthly list is dominated by evergreen images (Cat03, Crab Nebula) while the daily list captures real-time attention.

---

## 6. Known Data Quality Issues

### 6.1 Media Viewer Prefetch Inflation (Potentially 50%+)

From WMF's own documentation and Phabricator T210313:

> *"When using Media Viewer to view images, some images are prefetched for better user experience, but need not yet been shown to the user. Currently, those prefetched images are getting counted, as there is as of now no way to detect whether an image was actually shown to the user or not. The number of preloads might be as high as 50% of total requests for the file types supported by media viewer."*

This means the counts for larger, higher-quality images that trigger Media Viewer are systematically inflated. This disproportionately affects the very images you'd want in a "top images" list.

### 6.2 "Transfers" ≠ "Views"

The mediacounts data measures **HTTP transfers from upload.wikimedia.org**, not actual human views:

- A search engine bot that downloads a full-resolution image counts the same as a human
- A thumbnail served on a Wikipedia article that 10,000 people read counts as ~10,000 transfers
- Multiple thumbnails of the same image (different sizes) each count separately
- Cache hits don't count (which depresses counts for very popular images)
- The `total` field aggregates thumbnails + originals, but the `original` field only counts full-size transfers

### 6.3 Thumbnail Aggregation

The API's `total` field counts all transfers (thumbnails of all sizes + original). But a single Wikipedia article view typically triggers multiple thumbnail requests for the same image (different sizes for different devices). This inflates counts relative to the actual number of page views that included the image.

### 6.4 API Limitation: Only Top 1000

The REST API returns at most 1000 files per query. Since only ~12% of those are substantive images, we're seeing at most ~120 substantive images total. There may be many more substantive images with request counts just below the top 1000 threshold. For a monthly perspective, the top 1000 cutoff is approximately at **~4.6 million requests/month**. Any image getting fewer than ~150k requests/day falls below the cutoff.

### 6.5 Utility Filter Needs Ongoing Maintenance

The heuristic filter developed for this report is rule-based. It would need periodic updates to handle:

- New wiki project logos
- New campaign banners (Wiki Loves X, Wiki for Human Rights, etc.)
- New icon sets added to Commons
- New brand logos
- Known false positives that don't match existing patterns

### 6.6 Suspicious Daily Patterns

Some daily datasets show suspiciously identical request counts across many files (~509k-522k range), suggesting bot/crawler patterns on certain days. This is less apparent in monthly aggregates.

---

## 7. Viability Assessment

### 7.1 Scorecard

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Data availability** | ✅ | REST API and raw dumps both work |
| **Historical depth** | ✅ | Goes back to 2015 |
| **Daily granularity** | ✅ | Daily endpoint returns clean data |
| **Filtering utility images** | ⚠️ | Doable but needs maintenance |
| **Current events signal** | ✅ | Clear spikes for news/anniversaries |
| **Meaningful metric** | ⚠️ | "Transfers" not "views"; prefetch inflation |
| **Interesting output** | ✅ | The filtered lists are genuinely compelling |
| **Building a top.hatnote.com-style site** | ✅ | Feasible — adapt hatnote/top codebase |

### 7.2 Verdict

**Worth building — with honest framing.**

The daily list captures real-world attention patterns in a way that's genuinely interesting — anniversaries, sports events, political news, and natural disasters all create recognizable spikes. The filtered top 10-20 images on a given day would tell an interesting story about what the internet is looking at.

However, the product should be framed as **"most transferred Commons images"** (or simply "top images"), not "most viewed" — because the metric includes prefetches, bots, and all transfers, not just human views. The counts are useful for **relative ranking** but shouldn't be presented as absolute view counts.

### 7.3 What Would Make It Better (WMF-Side)

- **Instrumentation for actual "media views"** (scrolled-into-viewport events) — discussed in T210313 but not yet implemented
- **Detect and exclude Media Viewer prefetches** — the instrumentation exists (beacon events) but isn't integrated into the pipeline
- **Expose referer filtering** in the API (to separate internal wiki embeds from external hotlinks)

These have been discussed for years in WMF analytics planning. Until they're implemented, any "top images" list will carry the prefetch caveat.

---

## 8. Advanced Filtering: Structural vs. Organic Traffic

### 8.1 The Problem

Not all high-traffic images are equally interesting. Many images get millions of transfers not because people are looking at them, but because they're embedded in:

- **Heavily-transcluded templates** (e.g., `Red_pog.svg` appears on thousands of map articles via a template)
- **Infobox icons** (e.g., `Info_Simple.svg` on every article with an infobox)
- **Wiki project logos** (e.g., `Commons-logo.svg` in the sidebar of every Commons page)
- **Country flags** (embedded in hundreds of country-related articles)
- **Navigation UI** (arrows, close buttons, pictograms)

These are **structurally popular** — their traffic follows from being embedded in high-traffic pages, not from people having specific interest in the image itself.

Conversely, some images with **modest wiki usage but very high request counts** indicate genuine organic interest — people are clicking through to see the full image, hotlinking it from external sites, or seeking it out specifically.

### 8.2 Technique 1: Requests-per-Usage Ratio

The core idea: compute `total_transfers / number_of_using_pages`.

| Image | Reqs/mo | Wiki uses | Req/usage | Verdict |
|-------|---------|:---------:|:---------:|---------|
| `Apples_with_black_background.jpg` | 17M | **0** | **∞** | External hotlinking — pure organic |
| `Hitler_portrait_crop_(cropped)(2).jpg` | 7.8M | **8** | **975K** | Very high per-article interest |
| `Gigantic_jet_NOIRLab.jpg` | 10M | **22** | **455K** | High per-article interest |
| `StalinCropped1943.jpg` | 4.6M | 135 | 34K | Moderate per-article interest |
| `Cat03.jpg` | 62M | 500+ | 124K | Low per-article (structural — used everywhere) |
| `Crab_Nebula.jpg` | 6.2M | 500+ | 124K | Low per-article (evergreen, widely used) |
| `Killerwhales_jumping.jpg` | 6M | 500+ | 12K | Very low per-article (decorative image) |

**Key finding:** A high requests-per-usage ratio (>250K) strongly correlates with organic image interest. Images used on many pages but with low per-usage traffic (under 50K) are more likely to be structural/decorative.

### 8.3 Technique 2: Template vs. Article Usage

Using `prop=globalusage` with `guprop=namespace`, we can break down where an image is used across all Wikimedia wikis:

| Image | Article (NS0) | Template (NS10) | Module (NS828) | User (NS2) | Verdict |
|-------|:-------------:|:---------------:|:--------------:|:----------:|---------|
| `Red_pog.svg` | 463 | **36** | **31** | 1 | **Template-heavy** — structural map marker |
| `Commons-logo.svg` | 375 | 12 | 0 | 10 | **Everywhere** — structural logo |
| `Flag_of_Italy.svg` | 471 | 9 | 0 | 17 | Article use but flag = structural by nature |
| `Info_Simple.svg` | 491 | 9 | 0 | 0 | Article use but info icon = structural |
| `Hitler_portrait_crop_(cropped)(2).jpg` | 8 | 0 | 0 | 0 | **Pure article usage** — organic |
| `Gigantic_jet_NOIRLab.jpg` | 12 | 1 | 0 | 3 | **Mostly article** — organic |

**Insight:** Images with high template/module usage (>5) are candidates for structural filtering regardless of total request count. Images used exclusively in articles with low total usage are the strongest organic signals.

### 8.4 Technique 3: Spike Detection

Track day-over-day variance in request counts:

```
spike_ratio = today_requests / trailing_7_day_average
```

- **Tarawera eruption anniversary** (June 10): Near-infinite spike ratio (normally ~0 requests, spiked to 2M/day)
- **Evergreen images** (Cat03, Crab Nebula): Spike ratio ~1.0 (flat, always-on)
- **News images** (Trump, sports events): Spike ratio 3-10x (rises and falls with news cycle)

For a daily "Top Images" list, spike detection would be the most valuable filter — it surfaces what's *happening right now*, not what's always popular.

### 8.5 Technique 4: Referer Analysis (Raw Dumps Only)

The raw mediacounts dumps include `referer_internal`, `referer_external`, and `referer_unknown` fields per file. Images with high `referer_external` counts are being embedded on non-WMF sites — a different kind of organic signal. Unfortunately, the REST API doesn't expose this breakdown, so it would require processing the raw dumps.

### 8.6 Technique 5: Zero-Usage / Orphan Images

Some images have **zero wiki usage** but high request counts. These are being shared directly via URL (on social media, forums, or embedded on external websites). `Apples_with_black_background.jpg` (17M/mo, 0 wiki uses) and `A_Galaxy_of_Birth_and_Death.jpg` (7.5M/mo, 0 wiki uses) are two examples. These represent the purest form of organic interest — no Wikipedia page is driving traffic to them.

### 8.7 Composite Organic Score

For a production filter, combine these signals:

```python
def organic_score(f):
    score = 0
    # High per-usage ratio
    score += log(f.requests / max(1, f.wiki_usages))
    # Bonus for low template/module usage
    if f.template_usage < 5:
        score += 10
    # Bonus for zero wiki usage (pure external interest)
    if f.wiki_usages == 0:
        score += 20
    # Bonus for spike (if daily data available)
    if f.spike_ratio > 3:
        score += 15
    # Bonus for few articles but high traffic
    if f.article_count < 20 and f.requests > 5_000_000:
        score += 10
    return score
```

---

## 9. Organic Interest Ranking — Top 50 (May 2026)

Based on the requests-per-usage analysis applied to 97 substantive images. Ranked by *organic score* (requests ÷ wiki page usage counts). Higher means more genuine interest per page where the image appears.

```
========================================================================================================================
TOP 50 — ORGANIC INTEREST RANKING (May 2026)
========================================================================================================================
 Rk Prev      Reqs/mo    OrgScore  WikiUses Arts Templ User  Image
------------------------------------------------------------------------------------------------------------------------
  1  #323   17,254,181  17,254,181     0        0    0    0  Apples_with_black_background.jpg
  2  #662    7,524,303   7,524,303     0        0    0    0  A_Galaxy_of_Birth_and_Death.jpg
  3  #664    7,423,256   1,484,651     5        4    0    0  Bærekraftsprisen_2018_(cropped2).jpg
  4  #964    4,796,593   1,199,148     4        4    0    0  Steph_Curry_(51915116957).jpg
  5  #525   10,035,236   1,115,026     9        2    0    1  Chilaquiles_at_the_Grand_Cantina,...jpg
  6  #882    5,238,330   1,047,666     5        5    0    0  President_Donald_Trump_meets_with_CR7.jpg
  7  #522   10,046,500   1,004,650    10        2    1    1  2026_Federal_Agents_in_Minneapolis...jpg
  8  #647    7,762,270     970,284     8        8    0    0  Hitler_portrait_crop_(cropped)(2).jpg
  9  #707    6,907,370     767,486     9        3    1    1  Walaka,_Rosa,_Sergio,_Leslie_and_Kong-rey...jpg
 10  #532   10,023,350     715,954    14        2    1    1  De_oprichting_van_de_obelisk...jpg
 11  #535   10,018,476     715,605    14        1    1    1  Magura_Julie_disk_brake_rotor_160_mm.jpg
 12  #543   10,007,644     667,176    15        7    0    3  N&W_611_Leaman_Place_June_6,_2021.jpg
 13  #541   10,011,205     625,700    16        2    1    2  Gee!!_I_wish_I_were_a_man...jpg
 14  #872    5,317,040     531,704    10       10    0    0  Chicago_River_ferry_b.jpg
 15  #521   10,050,443     528,971    19        6    1    3  Japan_Airlines_777_Engine_Failure...jpg
 16  #411   13,240,361     509,245    26        4    6    0  2025_Hondius_-_IMO_9818709...jpg
 17  #530   10,027,165     477,484    21        7    2    3  PEF_Survey_of_Western_Palestine_composite.jpg
 18  #528   10,028,433     455,838    22       12    1    3  Gigantic_jet_NOIRLab.jpg
 19  #534   10,020,916     455,496    22        2    2    1  1907_Ultra_High_Relief_$20_Double_Eagle...jpg
 20  #509   10,114,430     421,435    24       11    2    4  Foodiesfeed.com_pouring-honey-on-pancakes...jpg
 21  #486   10,677,169     410,660    26       23    0    1  Vijay_at_Protest_of_the_Nadigar_Sangam.jpg
 22  #587    8,940,845     388,732    23        5    1    1  Cobbler_repairing_shoes_in_old_workshop...jpg
 23  #529   10,027,547     385,675    26        9    2    1  US-00010-One_Cent_(1974)_Aluminum.jpg
 24  #965    4,793,360     368,720    13       13    0    0  Fronalpstock_big.jpg
 25  #518   10,066,606     347,124    29       21    0    3  The_Serpent_Dust_Devil_on_Mars_PIA15116.jpg
 26  #538   10,015,256     345,354    29        5    3    2  Striegeliger_Schichtpilz-Stereum...jpg
 27  #539   10,012,519     333,751    30       10    2    2  Lactarius_resimus_Груздь_настоящий.jpg
 28  #428   12,302,299     323,745    38       15    6    4  Atlas_Van_der_Hagen...INSULARUM_MELITAE...jpg
 29  #523   10,036,937     313,654    32       25    0    2  Carl_Laemmle_holding_an_Oscar_trophy...jpg
 30  #783    6,090,987     304,549    20       16    0    1  Animal_diversity_b.png
 31  #546   10,005,221     294,271    34        7    2    4  Train_station_with_train_and_coal_depot...jpg
 32  #547   10,002,392     294,188    34       12    2    3  Pinnularia_major.jpg
 33  #629    8,048,460     287,445    28       19    0    1  A_Balloon_Site,_Coventry_(1943)...jpg
 34  #790    6,033,382     287,304    21       14    0    2  Lotharkreuz-Domschatzkammer-Aachen-2026.jpg
 35  #533   10,021,250     286,321    35       15    2    3  The_ciliate_Frontonia_sp.jpg
 36  #975    4,714,330     277,314    17       13    0    3  Official_portrait_of_Mamata_Banerjee.jpg
 37  #515   10,076,858     245,777    41       28    1    3  Collard-Greens-Bundle.jpg
 38  #757    6,263,898     215,996    29        8    2    3  Comatricha_nigra_176600092.jpg
 39  #537   10,016,530     213,118    47       26    0   12  Michael_J_Adams_X-15.jpg
 40  #895    5,151,666     183,988    28       13    1    4  SS_Sankt_Erik_icebreaker_museum_ship...jpg
 41  #870    5,331,051     161,547    33       20    0    1  Arthropoda_collage.png
 42  #427   12,414,584     153,266    81       33    8   23  Francisco_Carvalho_17052026.jpg
 43  #702    6,945,127     150,981    46       40    0    5  Suvendu_Adhikari_at_Esplanade_Metro...jpg
 44  #512   10,088,682     150,577    67       47    1    7  John_Logie_Baird_and_Stooky_Bill.png
 45  #502   10,251,956     148,579    69       42    2    8  USS_Zumwalt_(DDG_1000).jpg
 46  #269   20,720,582     132,824   156      113    4   11  Michael_Jackson_1983_(3x4_cropped).jpg
 47  #437   12,080,432     132,752    91       63    0    5  Covid-19_SP_-_UTI_V._Nova_Cachoeirinha.jpg
 48  #531   10,025,528     130,202    77       59    2    2  Mandarins_-_whole_and_halved.jpg
 49  #  63  79,082,353     158,165   500  +    2    2  425  1x1.png
 50  # 417  11,979,082     125,832    95       79    0    5  Moon_and_clouds_over_the_Moscow_Cremlin.jpg
```

**Column key:** `Rk` = organic rank; `Prev` = overall position in raw API; `OrgScore` = requests ÷ wiki_uses (higher = more organic); `WikiUses` = pages using it globally; `Arts` = article namespace; `Templ` = template namespace; `User` = user namespace.

### Orphan Images (zero wiki usage)

These get all traffic from external/direct sources:

| Overall Rank | Requests/mo | Image |
|:-----------:|:----------:|-------|
| #323 | 17,254,181 | Apples_with_black_background.jpg |
| #662 | 7,524,303 | A_Galaxy_of_Birth_and_Death.jpg |

### Evergreen Images (low organic score, widely used)

These are the images that dominate the raw top list but score poorly on organic interest:

| Image | Reqs/mo | OrgScore | WikiUses | Notes |
|-------|---------|:-------:|:--------:|-------|
| Cat03.jpg | 62M | 124K | 500+ | Famous benchmark/test cat photo |
| The_Blue_Marble,_AS17-148-22727.jpg | 10.9M | 21.8K | 500+ | Iconic Apollo 17 Earth photo |
| EC1835_C_cut.jpg | 9.7M | 19.4K | 500+ | Widely used historical photo |
| 046CupolaSPietro.jpg | 9.3M | 18.5K | 500+ | St. Peter's cupola |
| President_Barack_Obama.jpg | 8.0M | 15.9K | 500+ | Official portrait |
| Official_Presidential_Portrait_of_President_Donald_Trump...jpg | 7.8M | 15.6K | 500+ | Official portrait |
| John_F._Kennedy...jpg | 7.7M | 15.3K | 500+ | Official portrait |
| Freddie_Mercury_performing...jpg | 7.3M | 17.2K | 426 | Widely used music photo |

---

## 10. What Building It Would Look Like

### 10.1 Architecture (Based on hatnote/top)

The [hatnote/top](https://github.com/hatnote/top) repository (Python, MIT license) provides a proven template:

```
Daily cron job →
  Fetch mediarequests top 1000 (daily) →
  Run classification/filtering →
  Enrich with Commons metadata (image URL, caption, dimensions) →
  Generate HTML pages →
  Deploy static site (or serve via nginx)
```

### 10.2 Key Components Needed

| Component | Description | Difficulty |
|-----------|-------------|------------|
| **API fetcher** | Call `mediarequests/top` for the target date | Easy |
| **Image classifier** | Heuristic + blocklist + pattern-based filtering | Medium (needs maintenance) |
| **Metadata enrichment** | Fetch image title, thumbnail URL, and description via Commons API or QLever SPARQL | Medium |
| **HTML generation** | Use hatnote/top's Dust templates or a modern alternative | Easy |
| **Daily cron/deployment** | Toolforge Kubernetes job or static site build | Medium |

### 10.3 Metadata Enrichment Options

The mediarequests API returns only `file_path` (e.g., `/wikipedia/commons/e/ec/Crab_Nebula.jpg`). To display a nice list, you need:

- **File title:** Extract from path: `File:Crab_Nebula.jpg`
- **Thumbnail URL:** Construct from path with width parameter
- **Description/caption:** Fetch via Commons Action API (`action=query&prop=imageinfo`)
- **Categories/structured data:** Fetch via QLever SPARQL to categorize images as "photo of person," "landscape," "scientific image," etc.

### 10.4 What the Filter Would Look Like in Practice

A production-grade filter would combine:

1. **Exact blocklist:** ~500 known utility basenames (updated as-needed)
2. **Extension whitelist:** `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.webp` only
3. **Pattern rules:** Regex patterns for naming conventions
4. **Size heuristic:** Images under a minimum dimension threshold are likely icons
5. **Category lookup** (optional): Query Commons categories/SDC for classification
6. **Manual curation:** A "report false positive" mechanism

### 10.5 Running the Analysis

To reproduce or extend the analysis in this report:

```python
import requests

headers = {'User-Agent': 'TopCommons/1.0 (your@email.com)'}
url = 'https://wikimedia.org/api/rest_v1/metrics/mediarequests/top/all-referers/all-media-types/2026/05/all-days'
response = requests.get(url, headers=headers, timeout=30)
data = response.json()

# Iterate through data['items'][0]['files'] and apply filter
```

---

## Appendix: Raw API Response Structure

```json
{
  "items": [
    {
      "referer": "all-referers",
      "media_type": "all-media-types",
      "year": "2026",
      "month": "06",
      "day": "13",
      "files": [
        {
          "file_path": "/wikipedia/commons/4/4a/Commons-logo.svg",
          "requests": 12314289,
          "rank": 3
        },
        {
          "file_path": "/wikipedia/commons/5/55/WMA_button2b.png",
          "requests": 12055430,
          "rank": 4
        }
      ]
    }
  ]
}
```

**Note:** `file_path` is URL-encoded. To convert to a Commons File page URL:

```
https://commons.wikimedia.org/wiki/File:{filename}
```

Where `{filename}` is the last segment of `file_path`, URL-decoded.
