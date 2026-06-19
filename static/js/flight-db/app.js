/**
 * Flight DB — client-side dashboard for Zola static blog.
 * User-added flights & alliances persist in localStorage.
 * TODO: Replace localStorage with backend API when persistence is available.
 */
(function () {
  "use strict";

  const LS_FLIGHTS = "flightdb_flights_v1";
  const LS_ALLIANCES = "flightdb_alliances_v1";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  let seedFlights = [];
  let seedAlliances = [];

  function getBaseUrl() {
    const meta = document.querySelector('meta[name="zola-base-url"]');
    return meta ? meta.content.replace(/\/$/, "") : "";
  }

  function track(event, props) {
    props = props || {};
    try {
      if (typeof window.gtag === "function") {
        window.gtag("event", event, props);
      }
    } catch (_) { /* analytics unavailable */ }
  }

  function upper(val) {
    return (val || "").trim().toUpperCase();
  }

  function buildCombinator(airport, airline, flightNum) {
    return upper(airport) + upper(airline) + (flightNum || "").trim();
  }

  function isValidFlightNumber(num) {
    return /^[A-Z]{0,2}\d{1,4}[A-Z]?$/i.test((num || "").trim());
  }

  function isValidAirport(code) {
    return /^[A-Z]{3}$/.test(upper(code));
  }

  function isValidAirline(code) {
    return /^[A-Z0-9]{2}$/.test(upper(code));
  }

  function parseTime(t) {
    var m = (t || "").trim().match(/^(\d{1,2}):(\d{2})$/);
    if (!m) return null;
    var h = parseInt(m[1], 10);
    var min = parseInt(m[2], 10);
    if (h > 23 || min > 59) return null;
    return h * 60 + min;
  }

  function calcDuration(dep, arr) {
    var d = parseTime(dep);
    var a = parseTime(arr);
    if (d === null || a === null) return "";
    var diff = a - d;
    if (diff < 0) diff += 24 * 60;
    return Math.floor(diff / 60) + "h " + (diff % 60) + "m";
  }

  function initTimePicker(input) {
    if (!input) return;
    input.addEventListener("keydown", function (e) {
      if (e.key === "Tab" || e.key === "Escape") return;
      e.preventDefault();
    });
    input.addEventListener("paste", function (e) { e.preventDefault(); });
    input.addEventListener("click", function () {
      if (typeof input.showPicker === "function") {
        try { input.showPicker(); } catch (_) { /* unsupported */ }
      }
    });
  }

  function buildSuggestionLists() {
    var flights = getAllFlights().slice().sort(function (a, b) {
      return (b.addedAt || "").localeCompare(a.addedAt || "");
    });
    var lists = { airport: [], airline: [], flightNum: [], combinator: [] };
    var seen = { airport: {}, airline: {}, flightNum: {}, combinator: {} };
    flights.forEach(function (f) {
      [
        ["airport", f.airportCode],
        ["airline", f.airlineCode],
        ["flightNum", f.flightNumber],
        ["combinator", f.combinator],
      ].forEach(function (pair) {
        var key = pair[0];
        var val = (pair[1] || "").trim();
        if (!val || seen[key][val]) return;
        seen[key][val] = true;
        lists[key].push(val);
      });
    });
    return lists;
  }

  function initTypeahead(input, listEl, key) {
    if (!input || !listEl) return;
    var active = -1;

    function close() {
      listEl.hidden = true;
      listEl.classList.remove("flight-db__suggestions--open");
      input.setAttribute("aria-expanded", "false");
      active = -1;
    }

    function render() {
      var q = (input.value || "").trim();
      var all = buildSuggestionLists()[key] || [];
      var matches = q
        ? all.filter(function (v) { return v.toUpperCase().indexOf(q.toUpperCase()) === 0; })
        : all.slice(0, 8);
      matches = matches.slice(0, 8);
      if (!matches.length) { close(); return; }
      listEl.innerHTML = matches.map(function (v, i) {
        return '<li role="option" data-idx="' + i + '" data-val="' + v + '">' + v + "</li>";
      }).join("");
      listEl.hidden = false;
      listEl.classList.add("flight-db__suggestions--open");
      input.setAttribute("aria-expanded", "true");
      active = -1;
    }

    function pick(val) {
      input.value = val;
      close();
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    input.addEventListener("input", render);
    input.addEventListener("focus", render);
    input.addEventListener("keydown", function (e) {
      var items = $$("li", listEl);
      if (!items.length || listEl.hidden) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        active = Math.min(active + 1, items.length - 1);
        items.forEach(function (el, i) { el.classList.toggle("is-active", i === active); });
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        active = Math.max(active - 1, 0);
        items.forEach(function (el, i) { el.classList.toggle("is-active", i === active); });
      } else if (e.key === "Enter" && active >= 0) {
        e.preventDefault();
        pick(items[active].dataset.val);
      } else if (e.key === "Escape") {
        close();
      }
    });
    listEl.addEventListener("mousedown", function (e) {
      var li = e.target.closest("li[data-val]");
      if (li) { e.preventDefault(); pick(li.dataset.val); }
    });
    document.addEventListener("click", function (e) {
      if (!input.contains(e.target) && !listEl.contains(e.target)) close();
    });
  }

  function loadLS(key) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveLS(key, data) {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (_) { /* quota exceeded */ }
  }

  function getAllFlights() {
    return seedFlights.concat(loadLS(LS_FLIGHTS));
  }

  function getAllAlliances() {
    var custom = loadLS(LS_ALLIANCES);
    var map = {};
    seedAlliances.forEach(function (a) {
      map[upper(a.code)] = Object.assign({}, a, { code: upper(a.code) });
    });
    custom.forEach(function (a) {
      map[upper(a.code)] = Object.assign({}, a, { code: upper(a.code) });
    });
    return Object.keys(map).map(function (k) { return map[k]; });
  }

  function showToast(msg, type) {
    var el = $("#fdb-toast");
    if (!el) return;
    el.textContent = msg;
    el.className = "flight-db__toast flight-db__toast--" + (type || "success") + " flight-db__toast--show";
    clearTimeout(el._timer);
    el._timer = setTimeout(function () {
      el.classList.remove("flight-db__toast--show");
    }, 3200);
  }

  function initTabs() {
    var tabs = $$(".flight-db__tab");
    var panels = $$(".flight-db__panel");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var target = tab.dataset.tab;
        tabs.forEach(function (t) {
          t.classList.toggle("flight-db__tab--active", t === tab);
          t.setAttribute("aria-selected", t === tab ? "true" : "false");
        });
        panels.forEach(function (p) {
          var active = p.dataset.panel === target;
          p.classList.toggle("flight-db__panel--active", active);
          p.hidden = !active;
        });
      });
    });
  }

  function initAddFlight() {
    var form = $("#fdb-add-form");
    if (!form) return;

    var fields = {
      airport: $("#fdb-airport"),
      airline: $("#fdb-airline"),
      flightNum: $("#fdb-flight-num"),
      combinator: $("#fdb-combinator"),
      terminal: $("#fdb-terminal"),
      depTime: $("#fdb-dep-time"),
      arrAirport: $("#fdb-arr-airport"),
      arrTime: $("#fdb-arr-time"),
      duration: $("#fdb-duration"),
    };

    function syncCombinator() {
      fields.combinator.value = buildCombinator(
        fields.airport.value, fields.airline.value, fields.flightNum.value
      );
    }

    function syncDuration() {
      fields.duration.value = calcDuration(fields.depTime.value, fields.arrTime.value);
    }

    ["airport", "airline", "flightNum"].forEach(function (k) {
      fields[k].addEventListener("input", syncCombinator);
    });
    initTimePicker(fields.depTime);
    initTimePicker(fields.arrTime);
    ["depTime", "arrTime"].forEach(function (k) {
      fields[k].addEventListener("input", syncDuration);
      fields[k].addEventListener("change", syncDuration);
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var flight = {
        airportCode: upper(fields.airport.value),
        airlineCode: upper(fields.airline.value),
        flightNumber: fields.flightNum.value.trim(),
        combinator: fields.combinator.value,
        terminal: fields.terminal.value.trim(),
        departureTime: fields.depTime.value.trim(),
        arrivalAirport: upper(fields.arrAirport.value),
        arrivalTime: fields.arrTime.value.trim(),
        duration: fields.duration.value,
        addedAt: new Date().toISOString(),
      };

      if (!isValidAirport(flight.airportCode)) {
        showToast("Airport code phải 3 chữ cái (vd: ICN)", "error"); return;
      }
      if (!isValidAirline(flight.airlineCode)) {
        showToast("Airline code phải 2 ký tự (vd: PR)", "error"); return;
      }
      if (!isValidFlightNumber(flight.flightNumber)) {
        showToast("Flight number không hợp lệ", "error"); return;
      }
      if (!parseTime(flight.departureTime) || !parseTime(flight.arrivalTime)) {
        showToast("Giờ phải định dạng HH:MM", "error"); return;
      }
      if (!isValidAirport(flight.arrivalAirport)) {
        showToast("Arrival airport phải 3 chữ cái", "error"); return;
      }

      var all = getAllFlights();
      if (all.some(function (f) { return f.combinator === flight.combinator; })) {
        showToast("Combinator trùng: " + flight.combinator, "error"); return;
      }

      var stored = loadLS(LS_FLIGHTS);
      stored.push(flight);
      saveLS(LS_FLIGHTS, stored);
      track("flight_added", { combinator: flight.combinator });
      showToast("Đã thêm " + flight.combinator + "!");
      form.reset();
      fields.combinator.value = "";
      fields.duration.value = "";
    });
  }

  function renderFlightResults(flights) {
    var container = $("#fdb-search-results");
    if (!container) return;

    if (!flights.length) {
      container.innerHTML =
        '<div class="flight-db__empty"><span class="flight-db__empty-icon" aria-hidden="true">✈️</span>' +
        '<p>Không tìm thấy chuyến bay.</p>' +
        '<p class="flight-db__empty-hint">Thử airport, airline hoặc combinator khác.</p></div>';
      return;
    }

    var rows = flights.map(function (f) {
      return "<tr><td><span class=\"flight-db__badge\">" + f.combinator + "</span></td>" +
        "<td>" + f.airportCode + "</td><td>" + f.airlineCode + " " + f.flightNumber + "</td>" +
        "<td>T" + (f.terminal || "—") + "</td><td>" + f.departureTime + "</td>" +
        "<td>" + f.arrivalAirport + "</td><td>" + f.arrivalTime + "</td>" +
        "<td>" + (f.duration || "—") + "</td></tr>";
    }).join("");

    container.innerHTML =
      '<div class="flight-db__table-wrap"><table class="flight-db__table"><thead><tr>' +
      "<th>Combinator</th><th>From</th><th>Flight</th><th>Term</th>" +
      "<th>Departs</th><th>To</th><th>Arrives</th><th>Duration</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table></div>" +
      '<p class="flight-db__result-count">' + flights.length + " chuyến bay</p>";
  }

  function initSearchFlight() {
    var form = $("#fdb-search-form");
    if (!form) return;

    initTypeahead($("#fdb-s-airport"), $("#fdb-s-airport-list"), "airport");
    initTypeahead($("#fdb-s-airline"), $("#fdb-s-airline-list"), "airline");
    initTypeahead($("#fdb-s-flight-num"), $("#fdb-s-flight-num-list"), "flightNum");
    initTypeahead($("#fdb-s-combinator"), $("#fdb-s-combinator-list"), "combinator");

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var airport = upper($("#fdb-s-airport").value);
      var airline = upper($("#fdb-s-airline").value);
      var flightNum = $("#fdb-s-flight-num").value.trim();
      var combinator = upper($("#fdb-s-combinator").value);

      if (!airport && !airline && !flightNum && !combinator) {
        showToast("Nhập ít nhất một trường tìm kiếm", "error"); return;
      }

      var results = getAllFlights().filter(function (f) {
        if (airport && f.airportCode !== airport) return false;
        if (airline && f.airlineCode !== airline) return false;
        if (flightNum && f.flightNumber !== flightNum) return false;
        if (combinator && f.combinator !== combinator) return false;
        return true;
      });

      track("flight_searched", { results: results.length });
      renderFlightResults(results);
    });

    var clearBtn = $("#fdb-search-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        form.reset();
        $("#fdb-search-results").innerHTML =
          '<div class="flight-db__empty"><span class="flight-db__empty-icon" aria-hidden="true">🔍</span>' +
          '<p>Search your flight database</p>' +
          '<p class="flight-db__empty-hint">Filter by airport, airline, flight number, or combinator.</p></div>';
      });
    }
  }

  function renderAllianceResult(airline) {
    var container = $("#fdb-alliance-result");
    var addSection = $("#fdb-alliance-add");
    if (!container) return;

    if (!airline) {
      container.innerHTML =
        '<div class="flight-db__empty"><span class="flight-db__empty-icon" aria-hidden="true">🏢</span>' +
        '<p>Airline không có trong database.</p>' +
        '<p class="flight-db__empty-hint">Thêm bên dưới để mở rộng dữ liệu.</p></div>';
      if (addSection) addSection.hidden = false;
      return;
    }

    if (addSection) addSection.hidden = true;
    container.innerHTML =
      '<div class="flight-db__alliance-card flight-db__alliance-card--found">' +
      '<div class="flight-db__alliance-header">' +
      '<span class="flight-db__badge flight-db__badge--lg">' + airline.code + "</span>" +
      '<span class="flight-db__alliance-pill">' + airline.alliance + "</span></div>" +
      '<h3 class="flight-db__alliance-name">' + airline.name + "</h3>" +
      '<dl class="flight-db__dl">' +
      "<div><dt>Hub Airport</dt><dd>" + airline.hub + "</dd></div>" +
      "<div><dt>Hub City</dt><dd>" + airline.hubCity + "</dd></div>" +
      "<div><dt>Country</dt><dd>" + airline.country + "</dd></div></dl></div>";
  }

  function initAlliance() {
    var searchForm = $("#fdb-alliance-search-form");
    var addForm = $("#fdb-alliance-add-form");

    if (searchForm) {
      searchForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var code = upper($("#fdb-a-code").value);
        if (!isValidAirline(code)) {
          showToast("Nhập mã hãng 2 ký tự hợp lệ", "error"); return;
        }
        var found = getAllAlliances().find(function (a) { return a.code === code; });
        track("alliance_searched", { code: code, found: !!found });
        renderAllianceResult(found || null);
        if (!found) $("#fdb-add-code").value = code;
      });
    }

    if (addForm) {
      addForm.addEventListener("submit", function (e) {
        e.preventDefault();
        var entry = {
          code: upper($("#fdb-add-code").value),
          name: $("#fdb-add-name").value.trim(),
          alliance: $("#fdb-add-alliance").value.trim(),
          hub: upper($("#fdb-add-hub").value),
          hubCity: $("#fdb-add-hub-city").value.trim(),
          country: $("#fdb-add-country").value.trim(),
        };

        if (!isValidAirline(entry.code)) {
          showToast("Airline code phải 2 ký tự", "error"); return;
        }
        if (!entry.name || !entry.alliance) {
          showToast("Name và alliance bắt buộc", "error"); return;
        }
        if (!isValidAirport(entry.hub)) {
          showToast("Hub airport phải 3 chữ cái", "error"); return;
        }

        var stored = loadLS(LS_ALLIANCES);
        if (stored.some(function (a) { return upper(a.code) === entry.code; }) ||
            seedAlliances.some(function (a) { return upper(a.code) === entry.code; })) {
          showToast("Airline " + entry.code + " đã tồn tại", "error"); return;
        }

        stored.push(entry);
        saveLS(LS_ALLIANCES, stored);
        track("alliance_added", { code: entry.code });
        showToast(entry.code + " — " + entry.name + " đã thêm!");
        addForm.reset();
        renderAllianceResult(entry);
      });
    }
  }

  function loadSeedData() {
    var base = getBaseUrl();
    return Promise.all([
      fetch(base + "/data/flight-db/flights.json").then(function (r) { return r.ok ? r.json() : []; }),
      fetch(base + "/data/flight-db/alliances.json").then(function (r) { return r.ok ? r.json() : []; }),
    ]).then(function (data) {
      seedFlights = data[0] || [];
      seedAlliances = data[1] || [];
    }).catch(function () {
      seedFlights = [];
      seedAlliances = [];
    });
  }

  function init() {
    loadSeedData().then(function () {
      initTabs();
      initAddFlight();
      initSearchFlight();
      initAlliance();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
