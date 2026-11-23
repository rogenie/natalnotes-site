"""Sidereal horoscopes, monthly sky overviews and guides for mynatalnotes.com.

Posts live in content/posts/*.md with YAML front matter:

  kind: forecast | overview | guide
  title: the query, as people type it
  sign: scorpio            (forecast only)
  month: 2027-01           (forecast and overview)
  slug: rahu-ketu-...      (guide only)
  date: 2026-12-06         (publish date; future-dated posts are not built)
  description: 150-160 characters, the direct answer
  faq: [{q, a}, ...]       3-5 real follow-up questions

URLs:
  forecast  /sidereal-horoscope/<sign>/<month>-<year>/
  overview  /vedic-astrology/<month>-<year>/
  guide     /guides/<slug>/

check_post() fails the build if any date or degree in the text is not in the computed sky
(content/sky/<yyyy-mm>.json, made by sky.py), or if a post breaks the editorial rules.
"""
import json
import re
import datetime as dt
from pathlib import Path

import markdown
import yaml

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
HOUSE = {1: "self, body, how you come across", 2: "money, speech, family", 3: "effort, courage, siblings, messages",
         4: "home, mother, inner peace", 5: "creativity, romance, children, study", 6: "work, routines, health habits, conflict",
         7: "partners and close one-on-ones", 8: "change, shared money, what's hidden", 9: "beliefs, teachers, travel, luck",
         10: "career and reputation", 11: "gains, friends, goals", 12: "rest, endings, spending, the inner life"}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}
BANNED = [r"\bguarantee", r"\bdefinitely will\b", r"\byou will meet\b", r"\bget pregnant\b", r"\binvest in\b",
          r"\bbuy (?:stock|crypto)", r"\bdiagnos", r"\bcures?\b", r"\bproves?\b", r"\b100%"]
MIN_WORDS = {"forecast": 900, "overview": 700, "guide": 900}
MAX_WORDS = {"forecast": 1900, "overview": 1800, "guide": 2200}


def ordinal(n):
    return ORD.get(n, f"{n}th")


def month_label(ym):
    y, m = map(int, ym.split("-"))
    return f"{MONTHS[m - 1]} {y}"


def month_slug(ym):
    y, m = map(int, ym.split("-"))
    return f"{MONTHS[m - 1].lower()}-{y}"


def load_sky(root):
    return {p.stem: json.loads(p.read_text()) for p in sorted((root / "content" / "sky").glob("*.json"))}


def post_path(p):
    if p["kind"] == "forecast":
        return f"/sidereal-horoscope/{p['sign']}/{month_slug(p['month'])}/"
    if p["kind"] == "overview":
        return f"/vedic-astrology/{month_slug(p['month'])}/"
    return f"/guides/{p['slug']}/"


def load_posts(root, today):
    posts = []
    for f in sorted((root / "content" / "posts").glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        _, fm, body = raw.split("---", 2)
        p = yaml.safe_load(fm)
        p["body"], p["file"] = body.strip(), f.name
        if isinstance(p["date"], str):
            p["date"] = dt.date.fromisoformat(p["date"])
        if p["date"] > today:
            continue
        p["path"] = post_path(p)
        posts.append(p)
    posts.sort(key=lambda p: (p["date"], p["file"]))
    return posts


# ---------- accuracy check ----------

DEG_RE = re.compile(r"(\d{1,2})°(?:\s?(\d{1,2})['’′])?\s+(" + "|".join(SIGNS) + r")\b")
DATE_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:\s?[–-]\s?(\d{1,2}))?(?:,?\s+(\d{4}))?\b")


BODY_NAMES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu",
              "Uranus", "Neptune", "Pluto"]


def event_names(e):
    t = e["type"]
    if t in ("ingress", "station"):
        return {e["body"]}
    if t in ("conjunction", "opposition"):
        return set(e["bodies"])
    if t in ("new_moon", "full_moon"):
        return {"Moon"}
    return {"eclipse"}


def sky_facts(sky, months):
    """dates: {iso date: names involved}; degs: [(sign, degree, names)].
    A date or degree in the text only passes if its sentence names something that
    actually happens on that date, or sits at that degree."""
    dates, degs, edges = {}, [], set()
    for ym in months:
        d = sky.get(ym)
        if not d:
            continue
        y, m = map(int, ym.split("-"))
        first = dt.date(y, m, 1)
        last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
        edges |= {first.isoformat(), last.isoformat()}
        for e in d["events"]:
            names = event_names(e)
            dates.setdefault(e["date"], []).append(names)
            if e["type"] == "ingress":
                degs += [(e["sign"], 0.0, names), (e["sign"], 29.99, names)]
            elif "deg" in e:
                degs.append((e["sign"], e["deg"], names | ({"Sun", "Moon"} if "eclipse" in names or "Moon" in names else set())))
        for key in ("positions_start", "positions_mid", "positions_end"):
            for b, pos in d[key].items():
                if b != "Moon":
                    degs.append((pos["sign"], pos["deg"], {b}))
    return dates, degs, edges


def named(sentence):
    low = sentence.lower()
    out = {b for b in BODY_NAMES if b.lower() in low}
    if "eclipse" in low:
        out.add("eclipse")
    return out


def sentences(text):
    return [x for x in re.split(r"(?<=[.!?])\s+|\n|\|", text) if x.strip()]


def months_for(p, sky):
    if p["kind"] in ("forecast", "overview"):
        y, m = map(int, p["month"].split("-"))
        prev = f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"
        nxt = f"{y + (m == 12)}-{m % 12 + 1:02d}"
        return [prev, p["month"], nxt]
    return list(sky)


def check_post(p, sky):
    errs = []
    text = p["body"] + "\n" + "\n".join(f"{f['q']} {f['a']}" for f in p.get("faq", [])) + "\n" + p["description"]
    dates, degs, edges = sky_facts(sky, months_for(p, sky))
    if p["kind"] in ("forecast", "overview") and p["month"] not in sky:
        errs.append(f"no sky data for {p['month']}: run python3 sky.py {p['month']}")
    base_year = int(p["month"][:4]) if p.get("month") else p["date"].year
    for sent in sentences(text):
        here = named(sent)
        for m in DATE_RE.finditer(sent):
            mon, day, _, year = m.groups()
            mi = MONTHS.index(mon) + 1
            years = [int(year)] if year else [base_year, base_year + 1, base_year - 1]
            ok = False
            for y in years:
                try:
                    iso = dt.date(y, mi, int(day)).isoformat()
                except ValueError:
                    continue
                if iso in edges or any(n <= here for n in dates.get(iso, [])):
                    ok = True
            if not ok:
                errs.append(f"date doesn't match a computed event named in its sentence: '{m.group(0)}' in \"{sent.strip()[:90]}\"")
        for m in DEG_RE.finditer(sent):
            d, mins, sign = m.groups()
            val = int(d) + (int(mins) / 60 if mins else 0)
            tol = 0.35 if mins else 1.0
            if not any(s == sign and names <= here | {"Sun", "Moon"} and names & here and (abs(val - x) <= tol or (not mins and 0 <= x - val < 1.0))
                       for s, x, names in degs):
                errs.append(f"degree doesn't match a computed position named in its sentence: '{m.group(0)}' in \"{sent.strip()[:90]}\"")
    low = text.lower()
    for b in BANNED:
        if re.search(b, low):
            errs.append(f"banned phrase: '{b}'")
    words = len(re.findall(r"\b\w+\b", p["body"]))
    if not MIN_WORDS[p["kind"]] <= words <= MAX_WORDS[p["kind"]]:
        errs.append(f"{words} words; {p['kind']} needs {MIN_WORDS[p['kind']]}-{MAX_WORDS[p['kind']]}")
    if not p["body"].startswith("**"):
        errs.append("first paragraph must be the bold direct answer")
    if not 3 <= len(p.get("faq", [])) <= 5:
        errs.append("needs 3-5 FAQ entries")
    if not 120 <= len(p["description"]) <= 165:
        errs.append(f"description is {len(p['description'])} characters; keep it 120-165")
    if p["kind"] == "forecast" and p["sign"].title() not in SIGNS:
        errs.append(f"unknown sign {p['sign']}")
    return [f"{p['file']}: {e}" for e in errs]


# ---------- generated tables ----------

def describe(e):
    t = e["type"]
    if t == "ingress":
        return f"{e['body']} enters {e['sign']}" + (" (retrograde)" if e["retrograde"] and e["body"] not in ("Rahu", "Ketu") else "")
    if t == "station":
        return f"{e['body']} turns {e['direction']} at {e['dms']} {e['sign']}"
    if t == "new_moon":
        return f"New Moon at {e['dms']} {e['sign']}, {e['nakshatra']}"
    if t == "full_moon":
        return f"Full Moon at {e['dms']} {e['sign']}, {e['nakshatra']}"
    if t == "solar_eclipse":
        return f"{e['kind'].title()} solar eclipse at {e['dms']} {e['sign']}, {e['nakshatra']}"
    if t == "lunar_eclipse":
        return f"{e['kind'].title()} lunar eclipse at {e['dms']} {e['sign']}, {e['nakshatra']}"
    a, b = e["bodies"]
    if t == "conjunction":
        return f"{a} meets {b} at {e['dms']} {e['sign']}"
    return f"{a} opposite {b} ({a} at {e['dms']} {e['sign']})"


def house_of(sign, rising):
    return (SIGNS.index(sign) - SIGNS.index(rising)) % 12 + 1


def fmt_date(e):
    y, m, d = map(int, e["date"].split("-"))
    return f"{MONTHS[m - 1][:3]} {d}"


def key_dates(sky_m, rising, esc):
    rows = []
    for e in sky_m["events"]:
        h = house_of(e["sign"], rising)
        where = f"{ordinal(h)} house: {HOUSE[h]}"
        if e["type"] == "opposition":
            h2 = (h + 5) % 12 + 1
            where = f"{ordinal(h)} and {ordinal(h2)} houses"
        rows.append(f"<tr><td>{fmt_date(e)}</td><td>{esc(describe(e))}</td><td>{esc(where)}</td></tr>")
    return ('<div class="table-wrap"><table class="sky"><thead><tr><th scope="col">Date (ET)</th>'
            f'<th scope="col">What happens</th><th scope="col">For {esc(rising)} rising</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def all_dates(sky_m, esc):
    rows = "".join(f"<tr><td>{fmt_date(e)}</td><td>{e['time']}</td><td>{esc(describe(e))}</td></tr>" for e in sky_m["events"])
    return ('<div class="table-wrap"><table class="sky"><thead><tr><th scope="col">Date</th><th scope="col">Time (ET)</th>'
            '<th scope="col">What happens</th></tr></thead><tbody>' + rows + "</tbody></table></div>")


ORDER = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto"]


def positions_table(sky_m, esc, rising=None):
    head = '<th scope="col">Planet</th><th scope="col">Position</th><th scope="col">Nakshatra</th>'
    if rising:
        head += f'<th scope="col">{esc(rising)} house</th>'
    rows = []
    for b in ORDER:
        p = sky_m["positions_start"][b]
        r = " R" if p["retrograde"] else ""
        cells = f"<th scope=\"row\">{b}</th><td>{p['dms']} {p['sign']}{r}</td><td>{p['nakshatra']} {p['pada']}</td>"
        if rising:
            cells += f"<td>{ordinal(house_of(p['sign'], rising))}</td>"
        rows.append(f"<tr>{cells}</tr>")
    return ('<div class="table-wrap"><table class="sky"><thead><tr>' + head + "</tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>"
            + '<p class="table-note">Positions at the start of the month, sidereal (Lahiri). R means retrograde. Rahu and Ketu use the mean node.</p>')


def render_md(text):
    out = markdown.markdown(text, extensions=["extra", "sane_lists"])
    return out.replace("<table>", '<div class="table-wrap"><table class="sky">').replace("</table>", "</table></div>")


def word_count(p):
    return len(re.findall(r"\b\w+\b", p["body"]))
