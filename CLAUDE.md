# kamphey.com

Static personal site. Single page at `site/index.html`, images in `site/img/`. No build step.

- No em dashes anywhere in copy.
- Keep project blurbs to one or two short sentences.
- Design is "Plain": Source Sans 3, white / soft dark gray, projects as list rows, light/dark toggle top right. Readability first. The user rejected the cream/serif "Claude-made" look, pure black, neo-brutalist blocks and the editorial magazine look.
- `site/_themes/`, `_designs.html`, `_variants.html` are local-only previews, excluded from deploys by `site/.assetsignore`.
- Images: resize to max 900px and save as JPEG (`sips -s format jpeg -s formatOptions 78 -Z 900`).
- Deploy with `npx wrangler deploy` (Cloudflare, config in `wrangler.jsonc`).
