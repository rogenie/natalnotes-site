/* Natal Notes sign finder.
   Works out the Sun's ecliptic longitude on the birthday (noon UTC, low-precision solar
   formula from the Astronomical Almanac, accurate to about 0.01 degree), then:
     tropical sign = longitude / 30
     sidereal sign = (longitude - Lahiri ayanamsa) / 30
   Birth time isn't asked, so a birthday within about a degree of a sign change is flagged. */
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("journal-data").textContent);
  var input = document.getElementById("bday");
  var button = document.getElementById("bday-go");
  var out = document.getElementById("finder-result");
  var rad = Math.PI / 180;

  function mod(a, n) { return ((a % n) + n) % n; }

  function longitudes(y, m, d) {
    var jd = Date.UTC(y, m - 1, d, 12) / 864e5 + 2440587.5;
    var n = jd - 2451545.0;
    var L = mod(280.460 + 0.9856474 * n, 360);
    var g = mod(357.528 + 0.9856003 * n, 360) * rad;
    var trop = mod(L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g), 360);
    var ayanamsa = 23.857 + (n / 365.25) * 0.013969;   // Lahiri, degrees
    return { trop: trop, sid: mod(trop - ayanamsa, 360) };
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function card(label, j, cusp) {
    return '<div class="result-card">' +
      '<a href="/journals/' + j.slug + '/"><img src="/covers/' + j.slug + '.jpg" width="600" height="1025" alt="' + esc(j.s) + ' Daily Journal cover"></a>' +
      '<div class="result-text"><p class="result-label">' + label + '</p>' +
      '<p class="result-sign">' + esc(j.s) + '</p>' +
      (cusp ? '<p class="result-cusp">You were born right on the edge of ' + esc(cusp) + '. Your birth time decides it.</p>' : '') +
      '<a class="buy" href="' + esc(j.buy) + '" rel="sponsored noopener" target="_blank">Get it on Amazon</a>' +
      '<a class="more" href="/journals/' + j.slug + '/">The ' + esc(j.s) + ' pattern</a></div></div>';
  }

  function neighbour(deg) {
    var within = mod(deg, 30);
    if (within < 1) return data[mod(Math.floor(deg / 30) - 1, 12)].s;
    if (within > 29) return data[mod(Math.floor(deg / 30) + 1, 12)].s;
    return null;
  }

  function show() {
    var v = input.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) {
      out.hidden = false;
      out.innerHTML = '<p class="result-error">Enter your birthday as a full date, then press Show my signs.</p>';
      return;
    }
    var p = v.split("-").map(Number);
    var lon = longitudes(p[0], p[1], p[2]);
    var t = data[Math.floor(lon.trop / 30)], s = data[Math.floor(lon.sid / 30)];
    var html;
    if (t.slug === s.slug) {
      html = '<p class="result-head">Same sign in both zodiacs.</p>' + card("Tropical and sidereal", t, neighbour(lon.trop) || neighbour(lon.sid));
    } else {
      html = '<p class="result-head">Your horoscope says ' + esc(t.s) + '. The sky says ' + esc(s.s) + '.</p>' +
        '<div class="result-pair">' + card("Sidereal, from the real sky", s, neighbour(lon.sid)) +
        card("Tropical, the usual horoscope", t, neighbour(lon.trop)) + '</div>';
    }
    out.innerHTML = html;
    out.hidden = false;
    out.classList.remove("reveal"); void out.offsetWidth; out.classList.add("reveal");
  }

  button.addEventListener("click", show);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); show(); } });
  window.__natalLongitudes = longitudes;   // used by the build check
})();
