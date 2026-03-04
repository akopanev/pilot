#!/usr/bin/env bash
set -euo pipefail

# Fetch App Store reviews via Apple RSS feed (free, no API key).
# Reads app IDs from apps.json, saves reviews per app folder.

OUTPUT_DIR="$PILOT_CONFIG_DIR/$PILOT_APPTWEAK_OUTPUT_DIR"
APPS_JSON="$OUTPUT_DIR/apps.json"
COUNTRY="${PILOT_REVIEW_COUNTRY:-us}"
MAX_PAGES="${PILOT_REVIEW_PAGES:-2}"

if [ ! -f "$APPS_JSON" ]; then
  echo "<signal:failed>apps.json not found</signal:failed>"
  exit 1
fi

# Extract app IDs and slugified folder names from apps.json
APP_COUNT=$(python3 -c "import json; apps=json.load(open('$APPS_JSON')); print(len(apps))")
echo "<signal:update>fetching reviews for $APP_COUNT apps</signal:update>"

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

echo "<signal:ready>reviews fetched</signal:ready>"
