#!/usr/bin/env python3
"""Builds mynatalnotes.com from content/ into docs/ (served by GitHub Pages).

Usage: pip install pyyaml && python3 build.py
Content:
  content/site.yml      site settings, socials, sample affirmations
  content/journals.yml  the 12 journals (Amazon link, sign facts, copy)
  static/               style.css, finder.js, covers/<slug>.jpg
"""
import datetime as dt
import html
import json
import shutil
from pathlib import Path

import yaml

import posts as P

ROOT = Path(__file__).parent
CONTENT, STATIC, OUT = ROOT / "content", ROOT / "static", ROOT / "docs"
cfg = yaml.safe_load((CONTENT / "site.yml").read_text())
J = yaml.safe_load((CONTENT / "journals.yml").read_text())
BY = {j["slug"]: j for j in J}
TODAY = dt.date.today()
URL = cfg["url"].rstrip("/")
SKY = P.load_sky(ROOT)
POSTS = P.load_posts(ROOT, TODAY)
LASTMOD = {}

BOTS = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "PerplexityBot",
        "Perplexity-User", "ClaudeBot", "Claude-SearchBot", "Google-Extended", "Applebot",
        "Applebot-Extended", "DuckDuckBot"]

MOON = ('<svg class="moon" viewBox="0 0 64 64" aria-hidden="true"><defs><radialGradient id="mg" cx="35%" cy="40%" r="70%">'
        '<stop offset="0" stop-color="#f0b07a"/><stop offset="1" stop-color="#b8682f"/></radialGradient></defs>'
        '<path d="M42 6a27 27 0 1 0 16 44A23 23 0 1 1 42 6z" fill="url(#mg)"/></svg>')

ICONS = {
    "TikTok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.6 3c.4 2.2 1.8 3.7 4 3.9v3.2c-1.5 0-2.8-.4-4-1.2v6.1c0 3.4-2.7 6-6.1 6S4.4 18.4 4.4 15s2.7-6 6.1-6c.3 0 .6 0 .9.1v3.3a2.9 2.9 0 1 0 2 2.7V3h3.2z" fill="currentColor"/></svg>',
    "YouTube": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22.5 7.2a2.8 2.8 0 0 0-2-2C18.8 4.8 12 4.8 12 4.8s-6.8 0-8.5.4a2.8 2.8 0 0 0-2 2C1.1 8.9 1.1 12 1.1 12s0 3.1.4 4.8a2.8 2.8 0 0 0 2 2c1.7.4 8.5.4 8.5.4s6.8 0 8.5-.4a2.8 2.8 0 0 0 2-2c.4-1.7.4-4.8.4-4.8s0-3.1-.4-4.8zM9.8 15.1V8.9l5.6 3.1-5.6 3.1z" fill="currentColor"/></svg>',
    "Facebook": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 21.9v-7.6h2.6l.4-3h-3V9.4c0-.9.3-1.5 1.5-1.5h1.6V5.2c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.8v3h2.6v7.6h3.1z" fill="currentColor"/></svg>',
}


def esc(s):
    return html.escape(str(s), quote=True)


def socials(cls):
    return f'<nav class="{cls}" aria-label="Natal Notes on social media">' + "".join(
        f'<a href="{esc(s["url"])}" rel="me noopener" target="_blank" aria-label="Natal Notes on {esc(s["name"])}">'
        f'{ICONS.get(s["name"], "")}<span>{esc(s["name"])}</span></a>' for s in cfg.get("socials", [])) + "</nav>"


def buy(j, label=None, cls="buy"):
    label = label or f"Get the {j['sign']} journal on Amazon"
    return f'<a class="{cls}" href="{esc(j["buy"])}" rel="sponsored noopener" target="_blank">{esc(label)}</a>'


def cover(j, cls="cover", eager=False):
    return (f'<img class="{cls}" src="/covers/{j["slug"]}.jpg" width="600" height="1025" '
            f'alt="{esc(j["sign"])} Daily Journal cover: the {esc(j["sign"])} constellation on a night sky" '
            f'{"" if eager else "loading=\"lazy\" "}decoding="async">')


ORG = {"@context": "https://schema.org", "@type": "Organization", "name": cfg["name"], "url": URL + "/",
       "slogan": cfg["promise"], "sameAs": [s["url"] for s in cfg.get("socials", [])]}


def book_ld(j):
    return {"@context": "https://schema.org", "@type": "Book",
            "name": f"{j['sign']} Daily Journal", "bookFormat": "https://schema.org/Hardcover",
            "numberOfPages": 185, "inLanguage": "en", "brand": cfg["name"],
            "image": f"{URL}/covers/{j['slug']}.jpg", "url": f"{URL}/journals/{j['slug']}/",
            "description": f"A hardcover {j['sign']} daily journal with an affirmation on every one of its 185 pages.",
            "workExample": {"@type": "Book", "bookFormat": "https://schema.org/Hardcover",
                            "potentialAction": {"@type": "BuyAction", "target": j["buy"]}}}


def page(path, title, description, body, ld=(), kind="website", image=None, lastmod=None):
    full = title if title == cfg["name"] else f"{title} | {cfg['name']}"
    img = image or f"{URL}/covers/scorpio.jpg"
    gc = cfg.get("goatcounter") or ""
    track = (f'<script data-goatcounter="https://{esc(gc)}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n' if gc else "")
    lds = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in [ORG, *ld])
    nav = "".join(f'<a href="/journals/{j["slug"]}/">{esc(j["sign"])}</a>' for j in J)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{URL}{path}">
<meta name="theme-color" content="#050610">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="{esc(cfg['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{URL}{path}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/moon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Poppins:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
{track}{lds}</head>
<body>
<header class="masthead">
  <div class="wrap mast-inner">
    <a class="brand" href="/" aria-label="Natal Notes home">{MOON}<span class="brand-words"><span class="wordmark">NATAL NOTES</span><span class="brand-tag">{esc(cfg['tagline'])}</span></span></a>
    <nav class="top-nav"><a href="/#journals">Journals</a>{'<a href="/sidereal-horoscope/">Horoscopes</a>' if POSTS else ''}<a href="/sidereal-sign/">Your real sign</a></nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <p class="foot-line">{esc(cfg['promise'])}</p>
    {socials('foot-social')}
    <nav class="foot-signs" aria-label="All twelve journals">{nav}</nav>
    <p class="fine">{esc(cfg['associates_disclosure'])} Our forecasts describe planetary timing for reflection and planning, not certainties, and are never medical, legal or financial advice. &copy; {TODAY.year} Natal Notes, a 9nth Dimension LLC brand.</p>
  </div>
</footer>
</body>
</html>
"""
    dest = OUT / path.lstrip("/")
    if path.endswith("/"):
        dest = dest / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc, encoding="utf-8")
    SITEMAP.append(path)
    if lastmod:
        LASTMOD[path] = lastmod


SITEMAP = []


def finder(heading_tag="h2"):
    data = json.dumps([{"s": j["sign"], "slug": j["slug"], "buy": j["buy"]} for j in J])
    return f"""
<section class="finder" id="finder" aria-labelledby="finder-h">
  <div class="wrap finder-inner">
    <div class="finder-copy">
      <{heading_tag} id="finder-h">What's your real sign?</{heading_tag}>
      <p>Most horoscopes use the tropical zodiac, fixed to the seasons. Sidereal astrology uses where the
      constellations actually sit in the sky today, about 24 degrees away. Enter your birthday to see both.</p>
      <form class="finder-form" onsubmit="return false">
        <label for="bday">Your birthday</label>
        <div class="finder-row"><input id="bday" type="date" min="1900-01-01" max="2030-12-31" required><button type="submit" id="bday-go">Show my signs</button></div>
      </form>
    </div>
    <div class="finder-result" id="finder-result" aria-live="polite"><div class="placeholder"><span class="ph-cover"></span><span class="ph-cover"></span><p>Your sidereal and tropical signs, and the journal for each, show up here.</p></div></div>
  </div>
  <script type="application/json" id="journal-data">{data}</script>
  <script src="/finder.js" defer></script>
</section>"""


def latest_section():
    if not POSTS:
        return ""
    return f"""<section class="latest" aria-labelledby="latest-h"><div class="wrap narrow">
    <h2 id="latest-h">Sidereal horoscopes and guides</h2>
    {post_list(list(reversed(POSTS))[:5])}
    <p><a href="/sidereal-horoscope/">All sidereal horoscopes</a></p></div></section>"""


def build_home():
    shelf = "".join(
        f'<li class="shelf-item"><a class="shelf-link" href="/journals/{j["slug"]}/" aria-label="{esc(j["sign"])} journal">{cover(j)}</a>'
        f'{buy(j, "Shop on Amazon", "shelf-buy")}</li>' for j in J)
    affs = "".join(f'<li>{esc(a)}</li>' for a in cfg["sample_affirmations"])
    fan = "".join(cover(BY[s], "fan-cover", eager=True) for s in ("leo", "scorpio", "pisces"))
    body = f"""
<section class="hero">
  <div class="wrap hero-inner">
    <div class="hero-copy">
      <h1>Your sign explains you.<br><span>Your journal changes you.</span></h1>
      <p class="lede">Twelve hardcover Daily Journals, one for every sign. 185 pages, and every page opens with an affirmation, so the way you talk to yourself changes one morning at a time.</p>
      <div class="hero-actions"><a class="cta" href="#finder">Find my journal</a><a class="ghost" href="#journals">See all twelve</a></div>
    </div>
    <div class="fan" aria-hidden="true">{fan}</div>
  </div>
</section>
{finder()}
<section class="shelf-section" id="journals" aria-labelledby="journals-h">
  <div class="wrap">
    <h2 id="journals-h">Twelve signs, twelve journals</h2>
    <p class="section-sub">Tap a cover for that sign's pattern and the page to write tonight. Every journal ships from Amazon.</p>
    <ul class="shelf">{shelf}</ul>
  </div>
</section>
{latest_section()}
<section class="inside" aria-labelledby="inside-h">
  <div class="wrap inside-inner">
    <div class="page-mock" aria-hidden="true"><p class="page-aff">I powerfully attract what I want</p><span class="rule"></span><span class="rule"></span><span class="rule"></span><span class="rule"></span><span class="rule"></span><span class="rule"></span><span class="rule"></span></div>
    <div>
      <h2 id="inside-h">What's inside</h2>
      <dl class="specs">
        <div><dt>Pages</dt><dd>185 lined pages, an affirmation at the top of each one</dd></div>
        <div><dt>Cover</dt><dd>Hardcover, your sign's constellation on a night sky</dd></div>
        <div><dt>Size</dt><dd>5.5 × 8.5 inches, made to live in your bag</dd></div>
        <div><dt>How to use it</dt><dd>Read the line, believe it a little, then write whatever is actually on your mind</dd></div>
      </dl>
      <p class="aff-label">A few lines from the journal</p>
      <ul class="aff-list">{affs}</ul>
    </div>
  </div>
</section>
<section class="faq-section" aria-labelledby="faq-h">
  <div class="wrap narrow">
    <h2 id="faq-h">Questions</h2>
    <h3>Is this a guided workbook?</h3>
    <p>No. Each page gives you one affirmation and room to write. No homework, no fill-in-the-blanks. The sign pages on this site give you a prompt if you want one.</p>
    <h3>Should I get my tropical sign or my sidereal sign?</h3>
    <p>Natal Notes reads the sky sidereally, so we'd start with your sidereal sign. But if your tropical sign is the one you've always recognized yourself in, that's the one to write with. Use the finder above to see both.</p>
    <h3>Where do I buy it?</h3>
    <p>Every journal is printed and shipped by Amazon. The buttons on this site go straight to its Amazon page.</p>
    <h3>Will affirmations change my life?</h3>
    <p>We won't promise that. They're a daily practice for changing how you talk to yourself. What you do with that is the part that's yours.</p>
  </div>
</section>"""
    page("/", cfg["name"], cfg["description"], body)


def forecast_link(j):
    p = latest_for(j["slug"])
    if not p:
        return ""
    return f'<p class="forecast-link">This month for {esc(j["sign"])}: <a href="{p["path"]}">{esc(p["title"])}</a></p>'


def build_sign(j):
    i = J.index(j)
    prev_j, next_j = J[i - 1], J[(i + 1) % 12]
    others = "".join(
        f'<li><a href="/journals/{o["slug"]}/">{cover(o, "mini-cover")}<span>{esc(o["sign"])}</span></a></li>'
        for o in J if o is not j)
    faq = [
        {"q": f"What are the {j['sign']} dates?",
         "a": f"In the tropical zodiac most horoscopes use, {j['sign']} runs roughly {j['tropical']}. In sidereal astrology, which follows where the constellations sit today, it runs roughly {j['sidereal']}. Exact dates shift by a day or so from year to year."},
        {"q": f"What is {j['sign']}'s element and ruling planet?",
         "a": f"{j['sign']} is a {j['modality'].lower()} {j['element'].lower()} sign, ruled by {j['ruler']}."},
        {"q": f"What's inside the {j['sign']} Daily Journal?",
         "a": "185 lined pages in a 5.5 × 8.5 inch hardcover, and every page opens with an affirmation. It's a daily journal, not a guided workbook."},
    ]
    faq_html = "".join(f"<h3>{esc(f['q'])}</h3><p>{esc(f['a'])}</p>" for f in faq)
    body = f"""
<article class="sign-page">
  <div class="wrap sign-hero">
    <div class="sign-cover">{cover(j, "big-cover", eager=True)}</div>
    <div class="sign-intro">
      <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Natal Notes</a> / <a href="/#journals">Journals</a> / <span>{esc(j['sign'])}</span></nav>
      <h1>{esc(j['sign'])} Daily Journal</h1>
      <p class="lede">A hardcover journal for {esc(j['sign'])}: 185 pages, an affirmation at the top of every one.</p>
      {buy(j)}
      <dl class="facts">
        <div><dt>Element</dt><dd>{esc(j['element'])}</dd></div>
        <div><dt>Modality</dt><dd>{esc(j['modality'])}</dd></div>
        <div><dt>Ruled by</dt><dd>{esc(j['ruler'])}</dd></div>
        <div><dt>Tropical dates</dt><dd>{esc(j['tropical'])}</dd></div>
        <div><dt>Sidereal dates</dt><dd>{esc(j['sidereal'])}</dd></div>
      </dl>
      <p class="date-note">Sidereal and tropical dates differ by about three weeks. <a href="/sidereal-sign/">Check your real sign</a>.</p>
    </div>
  </div>
  <div class="wrap narrow sign-body">
    <h2>The {esc(j['sign'])} pattern</h2>
    <p>{esc(j['pattern'])}</p>
    {forecast_link(j)}
    <div class="pen">
      <h2>Write this tonight</h2>
      <p>{esc(j['pen'])}</p>
    </div>
    <figure class="quote">
      <blockquote>{esc(j['affirmation'])}</blockquote>
      <figcaption>A page from the journal</figcaption>
    </figure>
    <section class="faq-mini">{faq_html}</section>
    <p class="again">{buy(j, f"Get the {j['sign']} journal on Amazon", "buy")}</p>
    <nav class="steps" aria-label="Neighbouring signs"><a href="/journals/{prev_j['slug']}/">&larr; {esc(prev_j['sign'])}</a><a href="/journals/{next_j['slug']}/">{esc(next_j['sign'])} &rarr;</a></nav>
  </div>
  <section class="others" aria-labelledby="others-h">
    <div class="wrap"><h2 id="others-h">The other eleven</h2><ul class="mini-shelf">{others}</ul></div>
  </section>
</article>"""
    ld = [book_ld(j),
          {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Natal Notes", "item": URL + "/"},
              {"@type": "ListItem", "position": 2, "name": f"{j['sign']} Daily Journal", "item": f"{URL}/journals/{j['slug']}/"}]}]
    page(f"/journals/{j['slug']}/", f"{j['sign']} Daily Journal: affirmations on every page",
         f"The {j['sign']} Daily Journal: a hardcover with an affirmation on all 185 pages. {j['sign']} dates (tropical and sidereal), element, ruler, and a prompt to write tonight.",
         body, ld, kind="product", image=f"{URL}/covers/{j['slug']}.jpg")


def build_sidereal():
    rows = "".join(f"<tr><th scope=\"row\"><a href=\"/journals/{j['slug']}/\">{esc(j['sign'])}</a></th><td>{esc(j['tropical'])}</td><td>{esc(j['sidereal'])}</td></tr>" for j in J)
    body = f"""
<div class="wrap narrow side-head">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Natal Notes</a> / <span>Your real sign</span></nav>
  <h1>What's my sidereal sign?</h1>
  <p class="lede">Your sidereal sun sign is usually the sign before the one you grew up with. Enter your birthday below to see your tropical and sidereal signs side by side.</p>
</div>
{finder("h2")}
<div class="wrap narrow side-body">
  <h2>Why there are two zodiacs</h2>
  <p>The tropical zodiac, used by most Western horoscopes, starts Aries at the spring equinox. It follows the seasons. The sidereal zodiac, used in Vedic astrology and by Natal Notes, lines the signs up with the constellations where they appear in the sky now.</p>
  <p>Two thousand years ago the two lined up. Because the Earth's axis wobbles slowly (astronomers call it precession), they drift apart by about one degree every 72 years. Today the gap is roughly 24 degrees, which is why sidereal dates run about three weeks later.</p>
  <h2>Sidereal and tropical dates for every sign</h2>
  <div class="table-wrap"><table class="dates"><thead><tr><th scope="col">Sign</th><th scope="col">Tropical</th><th scope="col">Sidereal</th></tr></thead><tbody>{rows}</tbody></table></div>
  <p class="date-note">Dates are approximate and shift by a day or so from year to year. Born within a day of a change? Your birth time decides it, so check a full birth chart.</p>
  <h2>Which one is right?</h2>
  <p>Both are real systems with long histories, and astrologers disagree about which to use. We read the sky sidereally, and our monthly forecasts use the sidereal zodiac. Use the sign that helps you see yourself more clearly.</p>
</div>"""
    faq = [{"q": "What is a sidereal sign?", "a": "Your sidereal sign is the zodiac sign the Sun was in at your birth, measured against where the constellations actually sit in the sky, rather than against the seasons."},
           {"q": "Why is my sidereal sign different?", "a": "The tropical and sidereal zodiacs have drifted about 24 degrees apart because of the slow wobble of the Earth's axis, so most people's sidereal sign is the sign before their tropical one."}]
    ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]}]
    page("/sidereal-sign/", "What's my sidereal sign? Sidereal vs tropical zodiac",
         "Find your sidereal sun sign from your birthday, see sidereal and tropical dates for all twelve signs, and learn why the two zodiacs differ by about 24 degrees.", body, ld)


def crumbs(items):
    parts = [f'<a href="{u}">{esc(n)}</a>' if u else f"<span>{esc(n)}</span>" for n, u in items]
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(parts) + "</nav>"


def crumb_ld(items, path):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": URL + (u or path)}
        for i, (n, u) in enumerate(items)]}


def faq_ld(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq]}


def article_ld(p):
    return {"@context": "https://schema.org", "@type": "Article", "headline": p["title"], "description": p["description"],
            "datePublished": p["date"].isoformat(), "dateModified": str(p.get("updated", p["date"])),
            "author": {"@type": "Organization", "name": "The Natal Notes team", "url": URL + "/"},
            "publisher": {"@type": "Organization", "name": cfg["name"], "url": URL + "/",
                          "logo": {"@type": "ImageObject", "url": URL + "/moon.svg"}},
            "mainEntityOfPage": URL + p["path"], "inLanguage": "en",
            "image": f"{URL}/covers/{p.get('sign', 'scorpio')}.jpg"}


def journal_box(j):
    return f"""
<aside class="jbox" aria-label="The {esc(j['sign'])} Daily Journal">
  <a href="/journals/{j['slug']}/">{cover(j, "jbox-cover")}</a>
  <div>
    <p class="jbox-kicker">Write the month down</p>
    <h2>The {esc(j['sign'])} Daily Journal</h2>
    <p>185 hardcover pages, an affirmation at the top of every one. This month's line: <strong>{esc(j['affirmation'])}</strong></p>
    {buy(j)}
  </div>
</aside>"""


def faq_html(faq):
    return '<section class="faq-mini"><h2>Questions</h2>' + "".join(
        f"<h3>{esc(f['q'])}</h3><p>{esc(f['a'])}</p>" for f in faq) + "</section>"


def meta_line(p):
    d = p["date"]
    return (f'<p class="byline">By the Natal Notes team. Published {P.MONTHS[d.month - 1]} {d.day}, {d.year}. '
            'Sidereal zodiac (Lahiri), times in US Eastern.</p>')


def by_month():
    out = {}
    for p in POSTS:
        if p["kind"] in ("forecast", "overview"):
            out.setdefault(p["month"], {})[p.get("sign", "overview")] = p
    return dict(sorted(out.items(), reverse=True))


def sign_strip(ym, current=None):
    m = by_month().get(ym, {})
    items = []
    for j in J:
        p = m.get(j["slug"])
        if p and j["slug"] != current:
            items.append(f'<li><a href="{p["path"]}">{esc(j["sign"])}</a></li>')
        elif j["slug"] == current:
            items.append(f'<li><span aria-current="page">{esc(j["sign"])}</span></li>')
        else:
            items.append(f'<li><span class="soon">{esc(j["sign"])}</span></li>')
    return f'<nav class="sign-strip" aria-label="{esc(P.month_label(ym))} horoscopes by sign"><ul>' + "".join(items) + "</ul></nav>"


def inline_cta(j):
    return (f'<div class="cta-inline">{cover(j, "cta-cover")}<div><p><strong>The {esc(j["sign"])} Daily Journal.</strong> '
            f'185 hardcover pages, an affirmation on every one. A place to write this month down.</p>'
            f'{buy(j, f"Get the {j['sign']} journal on Amazon")}</div></div>')


def build_post(p):
    body_html = P.render_md(p["body"])
    jslug = p.get("sign") or p.get("journal")
    if jslug:
        body_html = body_html.replace("<p>{{buy}}</p>", inline_cta(BY[jslug]))
    if p["kind"] == "forecast":
        j = BY[p["sign"]]
        sky = SKY[p["month"]]
        label = P.month_label(p["month"])
        items = [("Natal Notes", "/"), ("Sidereal horoscopes", "/sidereal-horoscope/"),
                 (j["sign"], f"/sidereal-horoscope/{j['slug']}/"), (label, None)]
        ov = by_month().get(p["month"], {}).get("overview")
        prev = [q for q in POSTS if q["kind"] == "forecast" and q["sign"] == p["sign"] and q["month"] < p["month"]]
        extra = f"""
  <section class="sky-block"><h2>Key dates for {esc(j['sign'])} rising, {esc(label)}</h2>
  <p class="table-note">Each date shows the house it lights up when {esc(j['sign'])} is your rising sign. Reading for your moon sign? The same table works if your moon is in {esc(j['sign'])}.</p>
  {P.key_dates(sky, j['sign'], esc)}</section>
  <section class="sky-block"><h2>Where the planets sit for {esc(j['sign'])}</h2>{P.positions_table(sky, esc, j['sign'])}</section>
  {journal_box(j)}
  {faq_html(p['faq'])}
  <section class="more-links"><h2>{esc(label)} for every sign</h2>{sign_strip(p['month'], j['slug'])}
  {f'<p><a href="{ov["path"]}">The whole sky for {esc(label)}</a></p>' if ov else ''}
  {f'<p><a href="{prev[-1]["path"]}">{esc(j["sign"])} last month</a></p>' if prev else ''}</section>"""
        image = f"{URL}/covers/{j['slug']}.jpg"
    elif p["kind"] == "overview":
        sky = SKY[p["month"]]
        label = P.month_label(p["month"])
        items = [("Natal Notes", "/"), ("Sidereal horoscopes", "/sidereal-horoscope/"), (f"Vedic astrology {label}", None)]
        extra = f"""
  <section class="sky-block"><h2>Every planetary date in {esc(label)}</h2>{P.all_dates(sky, esc)}</section>
  <section class="sky-block"><h2>Planet positions on {esc(label.split()[0])} 1</h2>{P.positions_table(sky, esc)}</section>
  <section class="more-links"><h2>{esc(label)} horoscope for your sign</h2>{sign_strip(p['month'])}</section>
  {faq_html(p['faq'])}"""
        image = None
    else:
        items = [("Natal Notes", "/"), ("Guides", "/guides/"), (p["title"], None)]
        extra = faq_html(p["faq"]) + '<section class="more-links"><h2>Your real sign</h2><p>Not sure which sidereal sign you are? <a href="/sidereal-sign/">Find your sidereal sign from your birthday</a>.</p></section>'
        image = None
    body = f"""
<article class="post">
  <div class="wrap narrow">
    {crumbs(items)}
    <h1>{esc(p['title'])}</h1>
    {meta_line(p)}
    <div class="prose">{body_html}</div>
    {extra}
  </div>
</article>"""
    page(p["path"], p["title"], p["description"], body,
         [article_ld(p), faq_ld(p["faq"]), crumb_ld(items, p["path"])], kind="article", image=image,
         lastmod=str(p.get("updated", p["date"])))


def post_list(ps):
    return '<ul class="post-list">' + "".join(
        f'<li><a href="{p["path"]}">{esc(p["title"])}</a><span>{esc(p["description"])}</span></li>' for p in ps) + "</ul>"


def build_posts():
    for p in POSTS:
        build_post(p)
    if not POSTS:
        return
    bm = by_month()
    sections = []
    for ym, m in bm.items():
        label = P.month_label(ym)
        ov = m.get("overview")
        sections.append(f'<section class="month"><h2>{esc(label)}</h2>{sign_strip(ym)}'
                        + (f'<p><a href="{ov["path"]}">Vedic astrology {esc(label)}: every planetary date</a></p>' if ov else "") + "</section>")
    guides = [p for p in POSTS if p["kind"] == "guide"]
    body = f"""
<div class="wrap narrow side-head">
  {crumbs([("Natal Notes", "/"), ("Sidereal horoscopes", None)])}
  <h1>Sidereal horoscopes</h1>
  <p class="lede">Monthly sidereal (Vedic) forecasts for every sign, built from the real positions of the planets: the exact dates, degrees and nakshatras, and the house each one lights up for you. Read yours for your rising sign first, then your moon sign.</p>
</div>
<div class="wrap narrow side-body">
  {''.join(sections)}
  {('<h2>Guides</h2>' + post_list(reversed(guides))) if guides else ''}
</div>"""
    page("/sidereal-horoscope/", "Sidereal horoscopes: monthly Vedic forecasts for every sign",
         "Monthly sidereal horoscopes for all twelve signs, with exact planetary dates, degrees and nakshatras, and the house each transit lights up for your sign.", body)
    for j in J:
        fs = [p for p in POSTS if p["kind"] == "forecast" and p["sign"] == j["slug"]]
        if not fs:
            continue
        items = [("Natal Notes", "/"), ("Sidereal horoscopes", "/sidereal-horoscope/"), (j["sign"], None)]
        body = f"""
<div class="wrap narrow side-head">
  {crumbs(items)}
  <h1>{esc(j['sign'])} sidereal horoscope</h1>
  <p class="lede">Monthly sidereal (Vedic) forecasts for {esc(j['sign'])}. In the sidereal zodiac the Sun is in {esc(j['sign'])} roughly {esc(j['sidereal'])}, but these forecasts read best for {esc(j['sign'])} rising or a {esc(j['sign'])} moon.</p>
</div>
<div class="wrap narrow side-body">
  {post_list(reversed(fs))}
  {journal_box(j)}
</div>"""
        page(f"/sidereal-horoscope/{j['slug']}/", f"{j['sign']} sidereal horoscope: monthly Vedic forecast",
             f"Every monthly sidereal horoscope for {j['sign']} rising and {j['sign']} moon: exact planetary dates, degrees, nakshatras and houses, from the Natal Notes team.",
             body, [crumb_ld(items, f"/sidereal-horoscope/{j['slug']}/")], image=f"{URL}/covers/{j['slug']}.jpg")
    if guides:
        page("/guides/", "Sidereal astrology guides",
             "Guides to sidereal and Vedic astrology from Natal Notes: transits, eclipses, nakshatras, and how to read your sidereal chart.",
             f'<div class="wrap narrow side-head">{crumbs([("Natal Notes", "/"), ("Guides", None)])}<h1>Sidereal astrology guides</h1></div>'
             f'<div class="wrap narrow side-body">{post_list(reversed(guides))}</div>')


def latest_for(slug):
    fs = [p for p in POSTS if p["kind"] == "forecast" and p["sign"] == slug]
    return fs[-1] if fs else None


def build_files():
    robots = "\n\n".join(f"User-agent: {b}\nAllow: /" for b in BOTS) + f"\n\nUser-agent: *\nAllow: /\n\nSitemap: {URL}/sitemap.xml\n"
    (OUT / "robots.txt").write_text(robots)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(f"  <url><loc>{URL}{p}</loc><lastmod>{LASTMOD.get(p, TODAY)}</lastmod></url>" for p in SITEMAP if p != "/404.html")
                                     + "\n</urlset>\n")
    lines = [f"# {cfg['name']}", "", f"> {cfg['description']}", "", "## Journals", ""]
    lines += [f"- [{j['sign']} Daily Journal]({URL}/journals/{j['slug']}/): hardcover, 185 pages, an affirmation on every page. {j['element']}, {j['modality']}, ruled by {j['ruler']}. Tropical {j['tropical']}; sidereal {j['sidereal']}." for j in J]
    lines += ["", "## Guides", "", f"- [What's my sidereal sign?]({URL}/sidereal-sign/): sidereal vs tropical zodiac, with dates for every sign."]
    if POSTS:
        lines += ["", "## Sidereal horoscopes and guides", ""]
        lines += [f"- [{p['title']}]({URL}{p['path']}): {p['description']}" for p in reversed(POSTS)]
    (OUT / "llms.txt").write_text("\n".join(lines) + "\n")
    (OUT / "moon.svg").write_text(MOON.replace(' class="moon"', ' xmlns="http://www.w3.org/2000/svg"'))
    (OUT / ".nojekyll").write_text("")
    (OUT / "CNAME").write_text(cfg["custom_domain"] + "\n")
    for f in ("style.css", "finder.js"):
        shutil.copy(STATIC / f, OUT / f)
    shutil.copytree(STATIC / "covers", OUT / "covers")


def build():
    errs = [e for p in POSTS for e in P.check_post(p, SKY)]
    if errs:
        raise SystemExit("Post check failed:\n  " + "\n  ".join(errs))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    build_home()
    for j in J:
        build_sign(j)
    build_sidereal()
    build_posts()
    page("/404.html", "Page not found", "This page does not exist.",
         '<div class="wrap narrow side-head"><h1>Lost in space</h1><p>That page doesn\'t exist. <a href="/#journals">See all twelve journals</a>.</p></div>')
    build_files()
    print(f"Built {len(SITEMAP)} pages into docs/")


if __name__ == "__main__":
    build()
