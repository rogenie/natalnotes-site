"""Natal Notes sidereal sky engine.

Computes, for one calendar month, everything a monthly sidereal forecast is built on:
planet positions (Lahiri ayanamsa, Swiss Ephemeris / Moshier), sign ingresses,
retrograde and direct stations, new and full moons with their nakshatra, solar and
lunar eclipses, exact conjunctions and oppositions, and the whole-sign house each
planet falls in for every one of the 12 signs as a rising (or moon) sign.

Usage:
    python3 sky.py 2027-01          # writes content/sky/2027-01.json and prints a summary

Every date, degree and nakshatra that appears in a forecast must come from this file's
output. check_forecast() in build.py enforces that.
Times are US Eastern (America/New_York); the date is what a reader in the US sees.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

swe.set_sid_mode(swe.SIDM_LAHIRI)
FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
TZ = ZoneInfo("America/New_York")

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
              "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
              "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
              "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
              "Uttara Bhadrapada", "Revati"]
NAK_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

# Rahu uses the mean node, the usual Vedic convention.
BODIES = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
          "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Rahu": swe.MEAN_NODE,
          "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO}
GRAHAS = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]
STATIONERS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
INGRESS_BODIES = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu",
                  "Uranus", "Neptune", "Pluto"]
ASPECT_BODIES = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"]


def lon_speed(name, jd):
    if name == "Ketu":
        lon, spd = lon_speed("Rahu", jd)
        return (lon + 180) % 360, spd
    r = swe.calc_ut(jd, BODIES[name], FLAGS)[0]
    return r[0] % 360, r[3]


def lon(name, jd):
    return lon_speed(name, jd)[0]


def to_local(jd):
    y, m, d, h = swe.revjul(jd)
    utc = datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)
    return utc.astimezone(TZ)


def jd_of(dt):
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def place(deg):
    deg %= 360
    s = int(deg // 30)
    within = deg - s * 30
    n = int(deg // (360 / 27))
    pada = int((deg % (360 / 27)) // (360 / 108)) + 1
    return {"sign": SIGNS[s], "deg": round(within, 2), "dms": f"{int(within)}°{int((within % 1) * 60):02d}'",
            "nakshatra": NAKSHATRAS[n], "pada": pada, "nak_lord": NAK_LORDS[n % 9]}


def bisect(f, a, b, iters=40):
    """f changes sign between a and b; return the root."""
    fa = f(a)
    for _ in range(iters):
        m = (a + b) / 2
        fm = f(m)
        if (fa < 0) == (fm < 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def wrap(x):
    return (x + 180) % 360 - 180


def stamp(jd):
    t = to_local(jd)
    return {"jd": round(jd, 5), "date": t.strftime("%Y-%m-%d"), "time": t.strftime("%H:%M"),
            "label": t.strftime("%B %-d")}


def month_events(year, month):
    start = jd_of(datetime(year, month, 1, tzinfo=TZ))
    nm = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=TZ)
    end = jd_of(nm)
    step = 0.25
    events = []

    # Sign ingresses
    for b in INGRESS_BODIES:
        t = start
        while t < end:
            s0, s1 = int(lon(b, t) // 30), int(lon(b, t + step) // 30)
            if s0 != s1:
                bound = s1 * 30 if (s1 - s0) % 12 == 1 else s0 * 30
                r = bisect(lambda x: wrap(lon(b, x) - bound), t, t + step)
                if start <= r < end:
                    sp = lon_speed(b, r)[1]
                    events.append({"type": "ingress", "body": b, "sign": SIGNS[s1],
                                   "from": SIGNS[s0], "retrograde": sp < 0, **stamp(r)})
            t += step

    # Stations
    for b in STATIONERS:
        t = start - 1
        while t < end:
            v0, v1 = lon_speed(b, t)[1], lon_speed(b, t + step)[1]
            if (v0 < 0) != (v1 < 0):
                r = bisect(lambda x: lon_speed(b, x)[1], t, t + step)
                if start <= r < end:
                    events.append({"type": "station", "body": b,
                                   "direction": "retrograde" if v1 < 0 else "direct",
                                   **place(lon(b, r)), **stamp(r)})
            t += step

    # New and full moons
    def elong(x):
        return (lon("Moon", x) - lon("Sun", x)) % 360
    t = start
    while t < end:
        for target, kind in ((0, "new_moon"), (180, "full_moon")):
            a, c = wrap(elong(t) - target), wrap(elong(t + step) - target)
            if a < 0 <= c:
                r = bisect(lambda x: wrap(elong(x) - target), t, t + step)
                if start <= r < end:
                    events.append({"type": kind, **place(lon("Moon", r)), **stamp(r)})
        t += step

    # Eclipses (global)
    for kind, fn in (("solar_eclipse", swe.sol_eclipse_when_glob), ("lunar_eclipse", swe.lun_eclipse_when)):
        res = fn(start - 1, swe.FLG_MOSEPH)
        r = res[1][0]
        if start <= r < end:
            ecl = res[0]
            if ecl & swe.ECL_TOTAL:
                sub = "total"
            elif ecl & swe.ECL_ANNULAR:
                sub = "annular"
            elif ecl & swe.ECL_PARTIAL:
                sub = "partial"
            else:
                sub = "penumbral"
            body = "Sun" if kind == "solar_eclipse" else "Moon"
            events.append({"type": kind, "kind": sub, **place(lon(body, r)), **stamp(r)})

    # Conjunctions and oppositions between grahas (Rahu/Ketu pair skipped)
    pairs = [(a, b) for i, a in enumerate(ASPECT_BODIES) for b in ASPECT_BODIES[i + 1:]
             if {a, b} != {"Rahu", "Ketu"}]
    for a, b in pairs:
        for target, kind in ((0, "conjunction"), (180, "opposition")):
            if kind == "opposition" and ("Ketu" in (a, b) or "Rahu" in (a, b)):
                continue  # an opposition to Rahu is a conjunction with Ketu
            t = start
            while t < end:
                d0 = wrap(lon(a, t) - lon(b, t) - target)
                d1 = wrap(lon(a, t + step) - lon(b, t + step) - target)
                if (d0 < 0) != (d1 < 0) and abs(d0 - d1) < 90:
                    r = bisect(lambda x: wrap(lon(a, x) - lon(b, x) - target), t, t + step)
                    if start <= r < end:
                        events.append({"type": kind, "bodies": [a, b], **place(lon(a, r)), **stamp(r)})
                t += step

    events.sort(key=lambda e: e["jd"])
    return events, start, end


def positions(jd):
    out = {}
    for b in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu",
              "Uranus", "Neptune", "Pluto"]:
        l, s = lon_speed(b, jd)
        out[b] = {**place(l), "retrograde": s < 0 and b not in ("Rahu", "Ketu")}
    return out


def houses(pos):
    """For each rising/moon sign, the whole-sign house of each graha."""
    table = {}
    for i, sign in enumerate(SIGNS):
        table[sign] = {b: (SIGNS.index(pos[b]["sign"]) - i) % 12 + 1 for b in GRAHAS}
    return table


DRISHTI = {"Mars": (4, 7, 8), "Jupiter": (5, 7, 9), "Saturn": (3, 7, 10)}


def aspects(pos):
    """Vedic sign aspects (graha drishti): every graha aspects the 7th sign from itself;
    Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th."""
    out = {}
    for b in ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        i = SIGNS.index(pos[b]["sign"])
        out[b] = [SIGNS[(i + n - 1) % 12] for n in DRISHTI.get(b, (7,))]
    return out


def build(ym):
    year, month = map(int, ym.split("-"))
    events, start, end = month_events(year, month)
    mid = (start + end) / 2
    data = {
        "month": ym,
        "ayanamsa": "Lahiri",
        "ayanamsa_deg": round(swe.get_ayanamsa_ut(start), 4),
        "node": "mean",
        "timezone": "America/New_York",
        "positions_start": positions(start),
        "positions_mid": positions(mid),
        "positions_end": positions(end - 1e-4),
        "houses_start": houses(positions(start)),
        "aspects_start": aspects(positions(start)),
        "events": events,
    }
    path = Path(__file__).parent / "content" / "sky" / f"{ym}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return data, path


def summary(data):
    lines = [f"Sky for {data['month']} (Lahiri {data['ayanamsa_deg']}°, times ET)"]
    lines.append("Start of month:")
    for b, p in data["positions_start"].items():
        lines.append(f"  {b:8} {p['dms']:>7} {p['sign']:<12} {p['nakshatra']} {p['pada']}{'  R' if p['retrograde'] else ''}")
    lines.append("Events:")
    for e in data["events"]:
        if e["type"] == "ingress":
            d = f"{e['body']} enters {e['sign']}{' (retrograde)' if e['retrograde'] else ''}"
        elif e["type"] == "station":
            d = f"{e['body']} stations {e['direction']} at {e['dms']} {e['sign']} ({e['nakshatra']})"
        elif e["type"] in ("conjunction", "opposition"):
            d = f"{' '.join(e['bodies'])} {e['type']} at {e['dms']} {e['sign']} ({e['nakshatra']})"
        else:
            d = f"{e['type'].replace('_', ' ')} {e.get('kind', '')} at {e['dms']} {e['sign']} ({e['nakshatra']} {e['pada']})"
        lines.append(f"  {e['date']} {e['time']}  {d}")
    return "\n".join(lines)


if __name__ == "__main__":
    for ym in sys.argv[1:]:
        d, p = build(ym)
        print(summary(d))
        print("wrote", p)
