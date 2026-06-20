/* uptime-me.js — render tiny response-time sparklines for UPTIME_ME.
 * Reads server-injected JSON from [data-spark] (no API call, no external lib).
 * Defensive: any malformed entry is skipped; never throws. */
(function () {
  "use strict";

  function sparkline(points) {
    var vals = points.map(function (p) { return Number(p.ms); })
      .filter(function (v) { return isFinite(v) && v >= 0; });
    if (vals.length < 2) return null;
    var w = 160, h = 36, pad = 2;
    var max = Math.max.apply(null, vals);
    var min = Math.min.apply(null, vals);
    var span = max - min || 1;
    var step = (w - pad * 2) / (vals.length - 1);
    var coords = vals.map(function (v, i) {
      var x = pad + i * step;
      var y = h - pad - ((v - min) / span) * (h - pad * 2);
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("class", "uptime-spark__svg");
    svg.setAttribute("preserveAspectRatio", "none");
    var poly = document.createElementNS(ns, "polyline");
    poly.setAttribute("points", coords.join(" "));
    poly.setAttribute("fill", "none");
    poly.setAttribute("vector-effect", "non-scaling-stroke");
    svg.appendChild(poly);
    var last = document.createElementNS(ns, "circle");
    var lc = coords[coords.length - 1].split(",");
    last.setAttribute("cx", lc[0]);
    last.setAttribute("cy", lc[1]);
    last.setAttribute("r", "2.4");
    last.setAttribute("class", "uptime-spark__dot");
    svg.appendChild(last);
    return svg;
  }

  function init() {
    var nodes = document.querySelectorAll("[data-spark]");
    Array.prototype.forEach.call(nodes, function (el) {
      var pts;
      try { pts = JSON.parse(el.getAttribute("data-spark")); } catch (e) { return; }
      if (!Array.isArray(pts)) return;
      var svg = sparkline(pts);
      if (svg) { el.classList.add("uptime-spark"); el.appendChild(svg); }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
