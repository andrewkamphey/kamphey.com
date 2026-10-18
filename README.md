# kamphey.com

Andrew Kamphey's personal site: what I'm working on now, plus a timeline of years gone by. Replaces the old Carrd page.

Everything is one static page: `site/index.html`, with images in `site/img/`.

## Edit

- **Add a project:** copy one `<a class="card">` block in `site/index.html`, drop an image (about 900px wide, 16:9 looks best) in `site/img/`.
- **Add a year:** copy one `<li>` in the timeline. `class="big"` marks a highlight, `class="sold"` plus a `<span class="badge">Sold</span>` marks an exit.

## Preview

```bash
python3 -m http.server 8000 -d site
```

## Deploy (Cloudflare)

```bash
npx wrangler deploy
```

Needs kamphey.com's DNS on Cloudflare. GitHub Pages also works: serve the `site/` folder.
