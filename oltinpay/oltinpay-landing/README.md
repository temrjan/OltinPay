# OltinPay landing

Static pages served by Caddy straight off disk. No framework, no runtime, no
build step in production.

## `public/` is generated — do not edit it by hand

Pages are printed from `src/templates/` (markup, one set for every language) and
`src/strings/<lang>.json` (text). The result is committed, so `deploy.sh` and the
server work exactly as before: they still copy `public/` as it is.

```bash
python3 src/build.py           # print pages into public/
python3 src/build.py --check   # verify public/ matches the templates
python3 -m unittest discover -s src -p 'test_*.py'
```

Edit a page in `public/` and the next build silently overwrites it, so `--check`
runs in CI (`.github/workflows/landing.yml`) and fails the pull request instead.

## Adding or changing text

1. edit `src/templates/*.html` for structure, `src/strings/*.json` for words;
2. run `python3 src/build.py`;
3. commit `src/` **and** the regenerated `public/`.

The generator is deliberately dumb: `{{key}}` becomes a string, nothing else. No
conditionals, no loops, no pluralisation. If a page ever needs one of those, stop
and raise it rather than growing a template language here.

A key the templates do not use, and a placeholder no dictionary answers, both
fail the build. That is on purpose: a page with a hole in it looks fine in review.

## Serving

`Caddyfile` keeps clean URLs canonical — `/how-it-works`, not `/how-it-works.html`
— for the root and for every language subdirectory. Unknown paths fall through to
an honest 404 rather than the home page, which matters when a partner's security
scanner walks the site.

## Deploy

Merging does **not** publish. Run on the server:

```bash
REPO=/opt/oltinpay bash oltinpay/oltinpay-landing/deploy.sh
```
