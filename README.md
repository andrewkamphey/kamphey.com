# kamphey.com

Andrew Kamphey's personal site: a snapshot of what I'm working on now, plus a short "Before this" list. Replaces the old Carrd page.

Everything is one static page: `site/index.html`, with images in `site/img/`.

## Edit

- **Add a project:** copy one `<a class="card">` block in `site/index.html`, drop an image (about 900px wide, 16:9 looks best) in `site/img/`.
- **Add a past item:** copy one `<li>` under "Before this". `class="sold"` with `<span class="badge">Sold 2020</span>` marks an exit; `class="live"` with `<span class="badge live">Still going</span>` marks something still running.
- **Free things:** use `<span class="kind free">` for the green tag.

## Preview

```bash
python3 -m http.server 8000 -d site
```

## Deploy (Cloudflare)

```bash
npx wrangler deploy
```

Needs kamphey.com's DNS on Cloudflare. GitHub Pages also works: serve the `site/` folder.
