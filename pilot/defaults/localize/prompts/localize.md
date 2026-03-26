# Protocol: Localize Content

Item ID: `{{var:CURRENT_ID}}`
Output dir: `{{var:OUTPUT_DIR}}`
Locales: `{{var:LOCALES}}`

## Source Content (English)

```json
{{file:data/current_content.json}}
```

## Task

Translate this content into EVERY locale listed above. **Launch one Agent per locale — ALL agents in a single message — so they run in parallel.**

Each agent receives:
- The source content (copy the full JSON above into the agent prompt)
- The target locale
- The output file path: `{{var:OUTPUT_DIR}}/{locale}/{{var:CURRENT_ID}}.json`

Each agent must:
1. Translate `title`, `card_title`, and `article_markdown` into the target locale
2. Copy unchanged: `id` → `canonicalId`, `image_url` → `imageUrl`, `grounding_sources` → `sources`
3. Create the locale directory if needed
4. Write the output JSON file

## Output Format (each agent writes one file)

```json
{
  "type": "article",
  "locale": "<locale code>",
  "canonicalId": "<source id unchanged>",
  "meta": { "status": "published" },
  "data": {
    "title": "<translated title>",
    "card_title": "<translated card_title>",
    "markdown": "<translated article_markdown>",
    "imageUrl": "<source image_url unchanged>",
    "sources": ["<source grounding_sources array unchanged>"]
  }
}
```

## JSON Escaping (CRITICAL — include this in every agent prompt)

The `markdown` field is a JSON string containing Markdown. It MUST be properly escaped:

- Newlines → `\n`
- Double quotes → `\"`
- Backslashes → `\\`
- Tabs → `\t`

Do NOT use literal newlines inside JSON string values. Every line break in the markdown must be `\n` in the JSON string.

## Translation Rules (include in every agent prompt)

- Do NOT translate URLs, proper nouns, brand names, or technical terms commonly kept in English (e.g. NEAT, HIIT, Non-Exercise Activity Thermogenesis)
- The translation must read naturally in the target language — not word-for-word
- Keep the same tone, style, and paragraph structure as the original
- Preserve all Markdown formatting: headings (`##`), bullet points (`*`), bold (`**`), links
- `type` is always `"article"`, `meta.status` is always `"published"`
- Output valid JSON — no trailing commas, no comments

## Execution

1. Split the LOCALES string by comma
2. Launch ALL locale agents in a **single message** using the Agent tool (this makes them run in parallel)
3. Wait for all agents to complete
4. Emit: `<signal:completed>done</signal:completed>`

Do NOT process locales sequentially. All agents MUST be launched in one batch.
