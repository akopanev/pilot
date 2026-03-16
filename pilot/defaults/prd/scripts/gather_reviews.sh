#!/usr/bin/env bash
set -euo pipefail

# Fetch App Store reviews + app details (What's New, pricing) per competitor.
# Reads app IDs from apps.json, saves reviews.json and app_details.json per app folder.

OUTPUT_DIR="$PILOT_CONFIG_DIR/$PILOT_APPTWEAK_OUTPUT_DIR"
APPS_JSON="$OUTPUT_DIR/apps.json"
COUNTRY="${PILOT_REVIEW_COUNTRY:-us}"
MAX_PAGES="${PILOT_REVIEW_PAGES:-2}"

if [ ! -f "$APPS_JSON" ]; then
  echo "<signal:failed>apps.json not found</signal:failed>"
  exit 1
fi

APP_COUNT=$(python3 -c "import json; apps=json.load(open('$APPS_JSON')); print(len(apps))")
echo "<signal:update>fetching reviews + app details for $APP_COUNT apps</signal:update>"

python3 -c "
import json, os, urllib.request, sys

apps = json.load(open('$APPS_JSON'))
output_dir = '$OUTPUT_DIR'
country = '$COUNTRY'
max_pages = int('$MAX_PAGES')

for app in apps:
    app_id = app.get('_app_id', '')
    title = app.get('title', 'unknown')

    # Find the app's folder (slugified name — matches apptweak-fetch output)
    screenshots = app.get('screenshots_local', [])
    if not screenshots:
        print(f'  skip {title}: no folder found', file=sys.stderr)
        continue
    app_folder = os.path.dirname(screenshots[0])
    if not os.path.isdir(app_folder):
        print(f'  skip {title}: folder {app_folder} missing', file=sys.stderr)
        continue

    # --- App details via iTunes Lookup API (What's New, pricing, version) ---
    lookup_url = f'https://itunes.apple.com/lookup?id={app_id}&country={country}'
    try:
        req = urllib.request.Request(lookup_url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        lookup_data = json.loads(resp.read())
        results = lookup_data.get('results', [])
        if results:
            r = results[0]
            details = {
                'releaseNotes': r.get('releaseNotes', ''),
                'version': r.get('version', ''),
                'currentVersionReleaseDate': r.get('currentVersionReleaseDate', ''),
                'price': r.get('price', 0),
                'formattedPrice': r.get('formattedPrice', ''),
                'currency': r.get('currency', ''),
                'averageUserRating': r.get('averageUserRating', 0),
                'userRatingCount': r.get('userRatingCount', 0),
                'description': r.get('description', ''),
                'primaryGenreName': r.get('primaryGenreName', ''),
                'contentAdvisoryRating': r.get('contentAdvisoryRating', ''),
                'fileSizeBytes': r.get('fileSizeBytes', ''),
                'minimumOsVersion': r.get('minimumOsVersion', ''),
                'languageCodesISO2A': r.get('languageCodesISO2A', []),
            }
            details_path = os.path.join(app_folder, 'app_details.json')
            with open(details_path, 'w') as f:
                json.dump(details, f, indent=2, ensure_ascii=False)
            print(f'  {title}: details fetched (v{details[\"version\"]}, {details[\"formattedPrice\"]})')
        else:
            print(f'  {title}: no lookup results', file=sys.stderr)
    except Exception as e:
        print(f'  {title}: lookup failed: {e}', file=sys.stderr)

    # --- Reviews via Apple RSS feed ---
    reviews = []
    for page in range(1, max_pages + 1):
        url = (
            f'https://itunes.apple.com/{country}/rss/customerreviews/'
            f'page={page}/id={app_id}/sortBy=mostRecent/json'
        )
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            print(f'  {title} page {page}: {e}', file=sys.stderr)
            break

        entries = data.get('feed', {}).get('entry', [])
        if isinstance(entries, dict):
            entries = [entries]
        if not entries:
            break

        count = 0
        for entry in entries:
            if 'im:rating' not in entry:
                continue
            reviews.append({
                'rating': int(entry.get('im:rating', {}).get('label', 0)),
                'title': entry.get('title', {}).get('label', ''),
                'text': entry.get('content', {}).get('label', ''),
            })
            count += 1
        if count < 50:
            break

    out_path = os.path.join(app_folder, 'reviews.json')
    with open(out_path, 'w') as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)
    print(f'  {title}: {len(reviews)} reviews')
"

echo "<signal:ready>reviews + details fetched</signal:ready>"
