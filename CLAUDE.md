# Natal Notes site — how to work in this repo

Static site for mynatalnotes.com, served by GitHub Pages from `docs/` on `main`.
`pip install pyyaml markdown pyswisseph`, then `python3 build.py` regenerates `docs/`. Never hand-edit `docs/`.

## Files
- `content/journals.yml` the 12 journals (Amazon links). `content/site.yml` settings.
- `content/posts/<publish-date>-<slug>.md` horoscopes, monthly overviews, guides (front matter in `posts.py`).
- `content/calendar.yml` the publishing queue. `content/keywords.md` what people search.
- `sky.py` the ephemeris engine. `python3 sky.py 2027-01` writes `content/sky/2027-01.json`
  and prints every date, degree and nakshatra for the month. Sidereal, Lahiri ayanamsa, mean node, US Eastern time.

## Brand
- Reader: women 22-40 who know their sun, moon and rising and want depth, not fluff.
- Voice: a sharp, warm friend who knows the sky. Direct, specific, never vague, never doom.
- Sidereal (Vedic) only. Forecasts are written for the **Moon sign (rashi) first**, the way Vedic astrology reads
  transits (gochara is counted from the natal Moon; Sade Sati too), and for the rising sign second. Byline: the Natal Notes team.

## Accuracy (the build enforces this; do not work around it)
- Every date, degree, nakshatra, retrograde and house must come from `sky.py` output. Never from memory,
  never from another site. Run `python3 sky.py <month>` and read the summary before writing.
- `build.py` fails if a "Month D" date or "D°MM' Sign" degree in the text doesn't match an event or position
  that its sentence names. Fix the text, never the checker.
- Write dates as US Eastern dates, exactly as `sky.py` prints them.
- Nakshatra rulers (Vimshottari): Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury, repeating from Ashwini.
- Vedic aspects: every planet aspects the 7th sign from itself; Mars also 4th and 8th, Jupiter 5th and 9th,
  Saturn 3rd and 10th (`aspects_start` in the sky file). Houses are whole-sign (`houses_start`).
- Forecasts describe timing and themes ("a strong window for", "watch for", "favours"). Never promise events,
  never predict death, illness, pregnancy, accidents, or a specific person arriving. No medical, legal,
  financial or investment advice. Anything touching health, grief, anxiety or relationships in crisis
  gets a gentle line suggesting a doctor, counsellor or someone they trust.
- Joni Patry and other astrologers are a depth benchmark only. Never copy or paraphrase their text.

## Monthly forecast (kind: forecast) — the core product
Title: `<Sign> Moon Sign Horoscope <Month Year>: Sidereal Vedic Forecast`.
A forecast covers its calendar month by default. Only if Rogenie asks for a custom window, set `start:` and `end:`
in the front matter (the tables follow the window automatically) and put the dates in the title.
Description: 120-165 characters, the month's headline for that sign.
1,100-1,600 words (build allows 900-1,900). Structure:
1. Bold first paragraph, 40-60 words: the month's headline for this Moon sign, naming the 1-2 biggest transits and their houses.
   Then one line: the window dates, "counted from a <Sign> Moon", read again from your ascendant if you have <Sign> rising,
   and a link to /sidereal-sign/ to find your Moon sign.
2. `## What's the big picture for a <Sign> Moon right now?` Saturn, Jupiter, Rahu/Ketu: house from the Moon, nakshatra,
   retrograde, aspects, and whether Sade Sati applies (Saturn in the 12th, 1st or 2nd from the Moon). Classical gochara
   notes are welcome where they fit (e.g. the Sun in the 3rd, 6th, 10th or 11th from the Moon is favourable).
3. One H2 per major event of the month in date order (stations, ingresses of Sun/Mercury/Venus/Mars/Jupiter/Saturn, eclipses, New and Full Moon, tight conjunctions). Each gives date, degree, nakshatra, the house for this sign, and what it means in plain life terms: work, money, love, home, health habits. Phrase H2s as questions readers ask ("What does Mars retrograde in Leo mean for Scorpio?").
4. `## Love and relationships`, `## Career and money` short sections pulled from Venus, Mars, Jupiter, 5th/7th/10th/11th houses.
5. `## Best days and slow days` from the events.
6. A `<div class="practice" markdown="1">` with `### Write this month`: journal prompts for the window's New and Full Moon
   (people search "<sign> new moon / full moon journal prompts"), and the sign's affirmation from journals.yml, word for word.
7. Journal links: a link and a `{{buy}}` box right after the opening, a `{{buy}}` box mid-article, an inline link where
   journaling comes up naturally, and a closing "Write <Month> down" section with a link and `{{buy}}`.
The page adds the key-dates table, planet table, journal box, FAQ, and links automatically. 3-5 FAQ entries,
each a different follow-up ("Is January 2027 a good month for <Sign> to change jobs?").

## Monthly overview (kind: overview)
Title: `Vedic Astrology <Month Year>: Sidereal Transits, Dates and Eclipses`. Walk the month's events in date order
with what each means collectively. The full events and positions tables are added automatically.

## Guides (kind: guide)
Answer one searched question (see keywords.md). Bold direct answer first, H2s as follow-up questions,
a sign-by-sign section where it applies, one `practice` block, 3-5 FAQs.

## Publishing (scheduled task)
One post per run, at most one every ~2 days (40-hour guard). Take the first `planned` calendar entry whose `on`
date is today or earlier. Never backfill missed days, never publish two. Set the post's `date:` to today.
Generate sky data, write, run `python3 build.py` until it passes, check the page exists in `docs/`,
mark the calendar entry `status: published`, commit `Publish: <title>`, push to main.
Keep the calendar at least 6 weeks ahead: add the next month's overview, 12 forecasts (rotate sign order
by one) and guides from keywords.md when it runs short.
