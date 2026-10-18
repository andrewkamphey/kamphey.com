# kamphey.com

Static personal site. Single page at `site/index.html`, images in `site/img/`. No build step.

- No em dashes anywhere in copy.
- Keep project blurbs to one or two short sentences.
- Images: resize to max 900px and save as JPEG (`sips -s format jpeg -s formatOptions 78 -Z 900`).
- Deploy with `npx wrangler deploy` (Cloudflare, config in `wrangler.jsonc`).
