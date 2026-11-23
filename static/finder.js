/* Natal Notes sign finder.
   Sun: low-precision solar formula (Astronomical Almanac), about 0.01 degree.
   Moon: the 37 largest terms of Meeus' lunar theory (Astronomical Algorithms, ch. 47);
   checked against the Swiss Ephemeris over 1930-2030: max error 0.023 degree, about 3 minutes of time.
   Sidereal = tropical minus the Lahiri ayanamsa.
   The Moon changes sign every ~2.5 days, so it needs the birth time and the time zone of the
   birthplace (historical offsets come from the browser's time zone database). */
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("journal-data").textContent);
  var dateIn = document.getElementById("bday");
  var timeIn = document.getElementById("btime");
  var zoneIn = document.getElementById("bzone");
  var button = document.getElementById("bday-go");
  var out = document.getElementById("finder-result");
  var rad = Math.PI / 180;
  var SIGNS = data.map(function (j) { return j.s; });
  var SKY = { ev: [], house: {} };
  try { SKY = JSON.parse(document.getElementById("sky-data").textContent); } catch (e) {}
  var ORD = function (n) { return n + (n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th"); };
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function todayIso() { var t = new Date(); return t.getFullYear() + "-" + String(t.getMonth() + 1).padStart(2, "0") + "-" + String(t.getDate()).padStart(2, "0"); }
  function nice(iso) { var p = iso.split("-"); return MON[+p[1] - 1] + " " + (+p[2]); }

  // The prediction panel: the latest forecast for this Moon sign, and the next sky events
  // with the house each one lights up counted from that Moon.
  function predict(idx) {
    var j = data[idx], html = '<section class="predict"><p class="predict-kicker">Your prediction, ' + esc(j.s) + ' Moon</p>';
    if (j.f) {
      html += '<h3><a href="' + j.f.u + '">' + esc(j.f.t) + '</a></h3>';
      if (j.f.sum && j.f.sum.length) html += '<ul>' + j.f.sum.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>";
      html += '<a class="cta predict-go" href="' + j.f.u + '">Read my full prediction</a>';
    } else {
      html += '<h3>Your ' + esc(j.s) + ' forecast' + (j.next ? ' for ' + esc(j.next.m) + ' lands ' + esc(nice(j.next.on)) : ' is on its way') + '.</h3>' +
        '<p>Here\'s what the sky is doing for you until then.</p>';
    }
    var today = todayIso(), up = SKY.ev.filter(function (e) { return e.d >= today; }).slice(0, 4);
    if (up.length) {
      html += '<p class="predict-sub">Coming up for a ' + esc(j.s) + ' Moon</p><ol class="predict-ev">' + up.map(function (e) {
        var h = ((SIGNS.indexOf(e.s) - idx) % 12 + 12) % 12 + 1;
        return '<li><span class="pe-date">' + nice(e.d) + '</span><span>' + esc(e.w) + ' <em>' + ORD(h) + ' house: ' + esc(SKY.house[h] || "") + '</em></span></li>';
      }).join("") + "</ol>";
    }
    var sub = document.querySelector(".subscribe .sub-form");
    if (sub) html += '<p class="predict-foot"><a href="#" data-sub="' + esc(j.s) + '">Email me ' + esc(j.s) + '\'s next prediction</a></p>';
    return html + "</section>";
  }

  function mod(a, n) { return ((a % n) + n) % n; }

  // ---- time zones ----
  var here = "UTC";
  try { here = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch (e) {}
  var zones = [];
  try { zones = Intl.supportedValuesOf("timeZone"); } catch (e) {}
  if (!zones.length) zones = ["America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York", "Europe/London", "Asia/Kolkata", "Asia/Manila", "UTC"];
  if (zones.indexOf(here) < 0) zones.unshift(here);
  zoneIn.innerHTML = zones.map(function (z) {
    return '<option value="' + z + '"' + (z === here ? " selected" : "") + ">" + z.replace(/_/g, " ") + "</option>";
  }).join("");

  function offsetMs(zone, utcMs) {
    var f = new Intl.DateTimeFormat("en-US", { timeZone: zone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
    var p = {};
    f.formatToParts(new Date(utcMs)).forEach(function (x) { p[x.type] = x.value; });
    return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second) - utcMs;
  }

  function localToJd(y, m, d, hh, mm, zone) {
    var guess = Date.UTC(y, m - 1, d, hh, mm);
    var utc = guess - offsetMs(zone, guess);
    utc = guess - offsetMs(zone, utc);
    return utc / 864e5 + 2440587.5;
  }

  // ---- ephemeris ----
  function ayanamsa(jd) { return 23.857 + ((jd - 2451545.0) / 365.25) * 0.013969; }

  function sunTrop(jd) {
    var n = jd - 2451545.0;
    var L = mod(280.460 + 0.9856474 * n, 360);
    var g = mod(357.528 + 0.9856003 * n, 360) * rad;
    return mod(L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g), 360);
  }

  // [D, M, M', F, coefficient (1e-6 degree), power of E]
  var T = [[0,0,1,0,6288774,0],[2,0,-1,0,1274027,0],[2,0,0,0,658314,0],[0,0,2,0,213618,0],[0,1,0,0,-185116,1],[0,0,0,2,-114332,0],
    [2,0,-2,0,58793,0],[2,-1,-1,0,57066,1],[2,0,1,0,53322,0],[2,-1,0,0,45758,1],[0,1,-1,0,-40923,1],[1,0,0,0,-34720,0],[0,1,1,0,-30383,1],
    [2,0,0,-2,15327,0],[0,0,1,2,-12528,0],[0,0,1,-2,10980,0],[4,0,-1,0,10675,0],[0,0,3,0,10034,0],[4,0,-2,0,8548,0],[2,1,-1,0,-7888,1],
    [2,1,0,0,-6766,1],[1,0,-1,0,-5163,0],[1,1,0,0,4987,1],[2,-1,1,0,4036,1],[2,0,2,0,3994,0],[4,0,0,0,3861,0],[2,0,-3,0,3665,0],
    [0,1,-2,0,-2689,1],[2,0,-1,2,-2602,0],[2,-1,-2,0,2390,1],[1,0,1,0,-2348,0],[2,-2,0,0,2236,2],[0,1,2,0,-2120,1],[0,2,0,0,-2069,2]];

  function moonTrop(jd) {
    var t = (jd - 2451545.0) / 36525;
    var Lp = 218.3164477 + 481267.88123421 * t, D = 297.8501921 + 445267.1114034 * t;
    var M = 357.5291092 + 35999.0502909 * t, Mp = 134.9633964 + 477198.8675055 * t;
    var F = 93.2720950 + 483202.0175233 * t, E = 1 - 0.002516 * t;
    var s = 0;
    for (var i = 0; i < T.length; i++) {
      var r = T[i];
      s += r[4] * Math.pow(E, r[5]) * Math.sin((r[0] * D + r[1] * M + r[2] * Mp + r[3] * F) * rad);
    }
    s += 3958 * Math.sin((119.75 + 131.849 * t) * rad) + 1962 * Math.sin((Lp - F) * rad) + 318 * Math.sin((53.09 + 479264.290 * t) * rad);
    return mod(Lp + s / 1e6, 360);
  }

  function sid(trop, jd) { return mod(trop - ayanamsa(jd), 360); }
  function signOf(deg) { return Math.floor(deg / 30); }

  // When, in local clock time, the Moon crosses into the next sign during this day.
  function moonChange(y, m, d, zone) {
    var a = localToJd(y, m, d, 0, 0, zone), b = localToJd(y, m, d, 23, 59, zone);
    var s0 = signOf(sid(moonTrop(a), a)), s1 = signOf(sid(moonTrop(b), b));
    if (s0 === s1) return null;
    var lo = a, hi = b;
    for (var i = 0; i < 40; i++) {
      var mid = (lo + hi) / 2;
      if (signOf(sid(moonTrop(mid), mid)) === s0) lo = mid; else hi = mid;
    }
    var when = new Date((hi - 2440587.5) * 864e5);
    var label = new Intl.DateTimeFormat("en-US", { timeZone: zone, hour: "numeric", minute: "2-digit" }).format(when);
    return { from: s0, to: s1, label: label };
  }

  // ---- output ----
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function card(label, j, note, main) {
    return '<div class="result-card' + (main ? " main" : "") + '">' +
      '<a href="/journals/' + j.slug + '/"><img src="/covers/' + j.slug + '.jpg" width="600" height="1025" alt="' + esc(j.s) + ' Daily Journal cover"></a>' +
      '<div class="result-text"><p class="result-label">' + label + '</p>' +
      '<p class="result-sign">' + esc(j.s) + '</p>' +
      (note ? '<p class="result-cusp">' + note + '</p>' : '') +
      '<a class="buy" href="' + esc(j.buy) + '" rel="sponsored noopener" target="_blank">Get it on Amazon</a>' +
      '<a class="more" href="/journals/' + j.slug + '/">The ' + esc(j.s) + ' pattern</a></div></div>';
  }

  function edgeNote(deg) {
    var w = mod(deg, 30);
    if (w < 1) return "Born right at the start of " + SIGNS[signOf(deg)] + ". Check a full chart.";
    if (w > 29) return "Born right at the end of " + SIGNS[signOf(deg)] + ". Check a full chart.";
    return "";
  }

  function show() {
    var v = dateIn.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
      out.hidden = false;
      out.innerHTML = '<p class="result-error">Enter your birthday as a full date, then press Show my signs.</p>';
      return;
    }
    var p = v.split("-").map(Number), zone = zoneIn.value || "UTC";
    var hasTime = /^\d{2}:\d{2}/.test(timeIn.value);
    var hh = hasTime ? +timeIn.value.slice(0, 2) : 12, mm = hasTime ? +timeIn.value.slice(3, 5) : 0;
    var jd = localToJd(p[0], p[1], p[2], hh, mm, zone);
    var sunT = sunTrop(jd), sunS = sid(sunT, jd), moonS = sid(moonTrop(jd), jd);
    var moonCard, head;
    var change = moonChange(p[0], p[1], p[2], zone);

    if (hasTime) {
      var w = mod(moonS, 30), near = w < 0.3 || w > 29.7;
      moonCard = card("Sidereal Moon, your Vedic sign", data[signOf(moonS)],
        near ? "The Moon was changing signs within half an hour of this time. Double-check your birth time." : "", true);
      head = "Your Vedic Moon sign is " + esc(SIGNS[signOf(moonS)]) + ".";
    } else if (change) {
      moonCard = '<div class="result-note"><p class="result-label">Sidereal Moon, your Vedic sign</p>' +
        '<p>The Moon moved from <strong>' + esc(SIGNS[change.from]) + '</strong> into <strong>' + esc(SIGNS[change.to]) +
        '</strong> at about ' + esc(change.label) + ' that day. Born before then: ' + esc(SIGNS[change.from]) + ' Moon. After: ' +
        esc(SIGNS[change.to]) + ' Moon. Add your birth time to be sure.</p></div>';
      head = "Your Moon sign depends on your birth time.";
    } else {
      moonCard = card("Sidereal Moon, your Vedic sign", data[signOf(moonS)], "The Moon stayed in this sign all day, so your birth time doesn't change it.", true);
      head = "Your Vedic Moon sign is " + esc(SIGNS[signOf(moonS)]) + ".";
    }

    var t = data[signOf(sunT)], s = data[signOf(sunS)];
    var sunCards = t.slug === s.slug
      ? card("Sun sign, sidereal and tropical", t, edgeNote(sunT) || edgeNote(sunS))
      : card("Sidereal Sun, from the real sky", s, edgeNote(sunS)) + card("Tropical Sun, the usual horoscope", t, edgeNote(sunT));

    var primary = hasTime || !change ? signOf(moonS) : null;
    var pred = primary !== null ? predict(primary) : predict(change.from) + predict(change.to);
    out.innerHTML = '<p class="result-head">' + head + '</p>' + pred + '<p class="predict-sub">Your journals</p><div class="result-grid">' + moonCard + sunCards + '</div>' +
      '<p class="result-foot">Your rising sign needs your birth time and birthplace; a full Vedic birth chart shows it.</p>';
    out.hidden = false;
    out.classList.remove("reveal"); void out.offsetWidth; out.classList.add("reveal");
    if (window.innerWidth < 960) out.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  out.addEventListener("click", function (e) {
    var a = e.target.closest("[data-sub]");
    if (!a) return;
    e.preventDefault();
    var box = document.querySelector(".subscribe");
    var sel = box && box.querySelector("select");
    if (sel) sel.value = a.getAttribute("data-sub");
    if (box) { box.scrollIntoView({ behavior: "smooth", block: "center" }); var i = box.querySelector("input"); if (i) i.focus({ preventScroll: true }); }
  });
  button.addEventListener("click", show);
  [dateIn, timeIn].forEach(function (el) {
    el.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); show(); } });
  });
  window.__natal = { moonTrop: moonTrop, sunTrop: sunTrop, sid: sid, localToJd: localToJd };   // used by the build check
})();
