# Protocol: Localize Content

Locales: `{{var:LOCALES}}`

## Source Content (English)

```json
{{file:data/current_content.json}}
```

## Task

Translate the source content into every locale listed above **except `en`** (English is already saved).

For each target locale, translate:
- `title`
- `card_title`
- `article_markdown` — preserve all Markdown formatting exactly: headings (`##`), bullet points (`*`), bold (`**`), links

Do NOT translate:
- URLs
- Proper nouns, brand names, or technical terms commonly kept in English (e.g. NEAT, HIIT, Non-Exercise Activity Thermogenesis)

The translation must read naturally in the target language — not word-for-word. Keep the same tone, style, and paragraph structure.

## Output Format

Write a single JSON file to:

```
{{var:PILOT_CONFIG_DIR}}/data/translations.json
```

The file must be a JSON object keyed by locale code. Each value uses this exact structure:

```json
{
  "es": {
    "type": "article",
    "locale": "es",
    "canonicalId": "<source id unchanged>",
    "meta": { "status": "draft" },
    "data": {
      "title": "<translated title>",
      "card_title": "<translated card_title>",
      "markdown": "<translated article_markdown>",
      "imageUrl": "<source image_url unchanged>"
    }
  },
  "fr": { ... },
  "de": { ... }
}
```

## JSON Escaping (CRITICAL)

The `markdown` field is a JSON string containing Markdown. It MUST be properly escaped:

- Newlines → `\n`
- Double quotes → `\"`
- Backslashes → `\\`
- Tabs → `\t`

Do NOT use literal newlines inside JSON string values. Every line break in the markdown must be `\n` in the JSON string.

Example of a correct `markdown` value:
```
"The belief that real weight loss requires punishing gym sessions is completely false.\n\n## The Hidden Power\n\nHere is what is actually happening."
```

## Rules

- Include ALL locales from the list except `en`
- Each locale entry must have the exact structure shown above
- `canonicalId` and `imageUrl` are copied unchanged from the source
- `type` is always `"article"`
- `meta.status` is always `"draft"`
- Output valid JSON — no trailing commas, no comments
- Do not include any text outside the JSON file write

## Signals

- `<signal:update>progress</signal:update>` — progress updates
- `<signal:completed>done</signal:completed>` — when file is written
- `<signal:failed>reason</signal:failed>` — if translation cannot be completed
