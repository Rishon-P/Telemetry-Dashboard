/* ── Telemetry Dashboard App ─────────────────────── */
(function () {
  "use strict";

  /* ── Constants ─────────────────────────────────── */
  const GAUGE_RADIUS = 90;
  const CIRC = 2 * Math.PI * GAUGE_RADIUS;          // 565.49
  const ARC  = CIRC * 0.75;                          // 424.12  (270°)
  const START_ANGLE = 135;                            // degrees

  const GAUGES = {
    speed: { min: 0, max: 300, unit: "km/h", param: "speed_kmh",          key: "speed_kmh" },
    temp:  { min: 0, max: 150, unit: "°C",   param: "engine_temp_c",      key: "engine_temp_c" },
    psi:   { min: 0, max: 60,  unit: "PSI",  param: "tire_pressure_psi",  key: "tire_pressure_psi" },
  };

  /* ── Optimal automotive ranges (real-world data) ── */
  /*  Speed: typical passenger car highway limits                          */
  /*  Engine temp: 90°C nominal, 60-105°C normal operating (SAE J1349)   */
  /*  Tire pressure: 30-35 PSI recommended (US DOT / tire placard)        */
  const STATUS_RANGES = {
    speed: [
      { max: 120,  status: "optimal", label: "NORMAL" },
      { max: 160,  status: "warning", label: "HIGH SPEED" },
      { max: Infinity, status: "danger", label: "EXCESSIVE" },
    ],
    temp: [
      { max: 60,   status: "cold",    label: "COLD ENGINE" },
      { max: 105,  status: "optimal", label: "OPTIMAL" },
      { max: 115,  status: "warning", label: "OVERHEATING" },
      { max: Infinity, status: "danger", label: "CRITICAL" },
    ],
    psi: [
      { max: 25,   status: "danger",  label: "LOW DANGER" },
      { max: 30,   status: "warning", label: "UNDER-INFLATED" },
      { max: 35,   status: "optimal", label: "OPTIMAL" },
      { max: 40,   status: "warning", label: "OVER-INFLATED" },
      { max: Infinity, status: "danger", label: "HIGH DANGER" },
    ],
  };

  function getStatus(type, value) {
    const ranges = STATUS_RANGES[type];
    for (const r of ranges) {
      if (value <= r.max) return r;
    }
    return ranges[ranges.length - 1];
  }

  /* ── DOM refs ──────────────────────────────────── */
  const $  = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const connDot   = $(".conn-dot");
  const connLabel = $(".conn-label");
  const feedLog   = $(".feed-log");

  /* ── Build SVG tick marks ──────────────────────── */
  function buildTicks(svgEl, cfg) {
    const g = svgEl.querySelector(".gauge-ticks");
    if (!g) return;
    const cx = 120, cy = 120, r = GAUGE_RADIUS;
    const majorCount = 10;
    const minorPerMajor = 4;
    const totalMinor = majorCount * minorPerMajor;

    for (let i = 0; i <= totalMinor; i++) {
      const frac = i / totalMinor;
      const angle = (START_ANGLE + frac * 270) * (Math.PI / 180);
      const isMajor = i % minorPerMajor === 0;
      const innerR = isMajor ? r + 8 : r + 10;
      const outerR = isMajor ? r + 18 : r + 15;

      const x1 = cx + innerR * Math.cos(angle);
      const y1 = cy + innerR * Math.sin(angle);
      const x2 = cx + outerR * Math.cos(angle);
      const y2 = cy + outerR * Math.sin(angle);

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1); line.setAttribute("y1", y1);
      line.setAttribute("x2", x2); line.setAttribute("y2", y2);
      line.classList.add("gauge-tick");
      if (isMajor) line.classList.add("major");
      g.appendChild(line);

      /* Label for major ticks */
      if (isMajor) {
        const labelR = r + 27;
        const lx = cx + labelR * Math.cos(angle);
        const ly = cy + labelR * Math.sin(angle);
        const val = Math.round(cfg.min + frac * (cfg.max - cfg.min));
        const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
        txt.setAttribute("x", lx);
        txt.setAttribute("y", ly);
        txt.classList.add("gauge-tick-label");
        txt.textContent = val;
        g.appendChild(txt);
      }
    }
  }

  /* ── Gauge update ──────────────────────────────── */
  const STATUS_CLASSES = ["status-optimal", "status-warning", "status-danger", "status-cold"];

  function setGaugeValue(type, value) {
    const cfg = GAUGES[type];
    const clamped = Math.max(cfg.min, Math.min(cfg.max, value));
    const progress = (clamped - cfg.min) / (cfg.max - cfg.min);
    const offset = ARC * (1 - progress);

    const cardClass = type === "psi" ? "psi" : type;
    const arc   = $(`.gauge-card.${cardClass} .gauge-value-arc`);
    const num   = $(`.gauge-card.${cardClass} .gauge-number`);
    const badge = $(`.gauge-card.${cardClass} .status-badge`);

    if (arc) arc.style.strokeDashoffset = offset;
    if (num) {
      animateNumber(num, parseFloat(num.textContent) || 0, clamped, 400);
    }

    /* Apply status coloring */
    const st = getStatus(type, clamped);
    const cls = `status-${st.status}`;
    if (arc) { STATUS_CLASSES.forEach(c => arc.classList.remove(c)); arc.classList.add(cls); }
    if (num) { STATUS_CLASSES.forEach(c => num.classList.remove(c)); num.classList.add(cls); }
    if (badge) {
      badge.className = "status-badge " + st.status;
      badge.textContent = st.label;
    }
  }

  /* Smooth number animation */
  function animateNumber(el, from, to, duration) {
    const start = performance.now();
    const decimals = to % 1 !== 0 ? 1 : 0;
    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3);          // ease-out cubic
      const cur = from + (to - from) * ease;
      el.textContent = cur.toFixed(decimals);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ── Slider fill track ─────────────────────────── */
  function updateSliderFill(slider) {
    const min = parseFloat(slider.min);
    const max = parseFloat(slider.max);
    const val = parseFloat(slider.value);
    const pct = ((val - min) / (max - min)) * 100;
    const fill = slider.parentElement.querySelector(".slider-fill-track");
    if (fill) fill.style.width = pct + "%";
  }

  /* ── WebSocket ─────────────────────────────────── */
  let ws;
  let reconnectTimer;

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/telemetry`);

    ws.onopen = () => {
      connDot.classList.add("connected");
      connLabel.textContent = "CONNECTED";
      addFeedEntry("WebSocket connected", "system");
    };

    ws.onclose = () => {
      connDot.classList.remove("connected");
      connLabel.textContent = "DISCONNECTED";
      addFeedEntry("WebSocket disconnected — retrying…", "system");
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => { ws.close(); };

    ws.onmessage = (e) => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }

      if (msg.type === "telemetry" && msg.data) {
        setGaugeValue("speed", msg.data.speed_kmh);
        setGaugeValue("temp",  msg.data.engine_temp_c);
        setGaugeValue("psi",   msg.data.tire_pressure_psi);
        addFeedEntry(
          `SPD <span class="val-speed">${msg.data.speed_kmh}</span> · ` +
          `TMP <span class="val-temp">${msg.data.engine_temp_c}</span> · ` +
          `PSI <span class="val-psi">${msg.data.tire_pressure_psi}</span>`,
          "data"
        );
      } else if (msg.type === "ack") {
        addFeedEntry(`✓ ${msg.detail}`, "ack");
      } else if (msg.type === "error") {
        addFeedEntry(`✗ ${msg.detail}`, "error");
      }
    };
  }

  /* ── Feed log ──────────────────────────────────── */
  let feedCount = 0;
  function addFeedEntry(html, kind) {
    const now = new Date();
    const ts = now.toLocaleTimeString("en-GB", { hour12: false });
    const div = document.createElement("div");
    div.classList.add("entry");
    div.innerHTML = `<span class="ts">[${ts}]</span> ${html}`;
    feedLog.appendChild(div);

    // Keep max 80 entries
    feedCount++;
    if (feedCount > 80) {
      feedLog.removeChild(feedLog.firstChild);
      feedCount--;
    }
    feedLog.scrollTop = feedLog.scrollHeight;
  }

  /* ── Init ──────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    // Build ticks for each gauge
    Object.entries(GAUGES).forEach(([type, cfg]) => {
      const cardClass = type === "psi" ? "psi" : type;
      const svg = $(`.gauge-card.${cardClass} .gauge-svg`);
      if (svg) buildTicks(svg, cfg);
    });

    // Set initial arc attributes
    $$(".gauge-value-arc, .gauge-bg-arc").forEach((el) => {
      el.setAttribute("stroke-dasharray", `${ARC} ${CIRC}`);
    });
    $$(".gauge-value-arc").forEach((el) => {
      el.style.strokeDashoffset = ARC;      // 0%
    });

    // Slider events
    $$("input[type='range']").forEach((slider) => {
      updateSliderFill(slider);
      updateSliderStatus(slider); // initial status
      slider.addEventListener("input", () => {
        const display = slider.closest(".control-card").querySelector(".slider-value-display");
        const cfg = GAUGES[slider.dataset.gauge];
        display.textContent = `${slider.value} ${cfg.unit}`;
        updateSliderFill(slider);
        updateSliderStatus(slider);
      });
    });

    // Apply buttons
    $$(".btn-apply").forEach((btn) => {
      btn.addEventListener("click", () => {
        const card = btn.closest(".control-card");
        const slider = card.querySelector("input[type='range']");
        const gauge = slider.dataset.gauge;
        const cfg = GAUGES[gauge];
        const value = parseFloat(slider.value);

        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "update", parameter: cfg.param, value }));
          btn.classList.add("sent");
          btn.textContent = "SENT ✓";
          setTimeout(() => {
            btn.classList.remove("sent");
            btn.textContent = "APPLY";
          }, 1200);
        }
      });
    });

    // Feed toggle
    const feedHeader = $(".feed-header");
    const feedToggle = $(".feed-toggle");
    if (feedHeader) {
      feedHeader.addEventListener("click", () => {
        feedLog.classList.toggle("collapsed");
        feedToggle.classList.toggle("open");
      });
    }

    // Connect WS
    connect();
  });

  /* ── Slider status coloring ────────────────────── */
  function updateSliderStatus(slider) {
    const gauge = slider.dataset.gauge;
    const val = parseFloat(slider.value);
    const st = getStatus(gauge, val);
    const display = slider.closest(".control-card").querySelector(".slider-value-display");
    if (display) {
      STATUS_CLASSES.forEach(c => display.classList.remove(c));
      display.classList.add(`status-${st.status}`);
    }
  }
})();
