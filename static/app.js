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
    rpm:   { min: 0, max: 7000, unit: "RPM", param: "engine_rpm",         key: "engine_rpm" },
    throttle: { min: 0, max: 100, unit: "%", param: "throttle_pct", key: "throttle_pct" },
    load: { min: 0, max: 100, unit: "%", param: "engine_load_pct", key: "engine_load_pct" },
    maf: { min: 0, max: 655, unit: "g/s", param: "maf_g_sec", key: "maf_g_sec" },
    oil:   { min: 0, max: 100, unit: "PSI",  param: "oil_pressure_psi",   key: "oil_pressure_psi" },
    battery: { min: 0, max: 16, unit: "V", param: "battery_voltage_v",  key: "battery_voltage_v" },
    fuel:    { min: 0, max: 100, unit: "%", param: "fuel_level_pct",     key: "fuel_level_pct" },
    tire_fl: { min: 0, max: 60, unit: "PSI", param: "tire_pressure_fl_psi", key: "tire_pressure_fl_psi" },
    tire_fr: { min: 0, max: 60, unit: "PSI", param: "tire_pressure_fr_psi", key: "tire_pressure_fr_psi" },
    tire_rl: { min: 0, max: 60, unit: "PSI", param: "tire_pressure_rl_psi", key: "tire_pressure_rl_psi" },
    tire_rr: { min: 0, max: 60, unit: "PSI", param: "tire_pressure_rr_psi", key: "tire_pressure_rr_psi" },
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
    rpm: [
      { max: 500,  status: "danger",  label: "STALLED" },
      { max: 1000, status: "optimal", label: "IDLE" },
      { max: 3000, status: "optimal", label: "CRUISING" },
      { max: 5500, status: "warning", label: "HIGH RPM" },
      { max: 6500, status: "danger",  label: "REDLINE" },
      { max: Infinity, status: "danger", label: "OVER-REV" },
    ],
    oil: [
      { max: 15,   status: "danger",  label: "CRITICAL" },
      { max: 25,   status: "warning", label: "LOW" },
      { max: 65,   status: "optimal", label: "OPTIMAL" },
      { max: 75,   status: "warning", label: "HIGH" },
      { max: Infinity, status: "danger", label: "CRITICAL HIGH" },
    ],
    battery: [
      { max: 12.0, status: "danger",  label: "CRITICAL" },
      { max: 12.6, status: "warning", label: "LOW" },
      { max: 14.7, status: "optimal", label: "OPTIMAL" },
      { max: 15.5, status: "warning", label: "HIGH" },
      { max: Infinity, status: "danger", label: "CRITICAL HIGH" },
    ],
        throttle: [
      { max: 50, status: "optimal", label: "NORMAL" },
      { max: 85, status: "warning", label: "HIGH" },
      { max: Infinity, status: "danger", label: "WOT" },
    ],
    load: [
      { max: 40, status: "optimal", label: "LIGHT" },
      { max: 80, status: "warning", label: "HEAVY" },
      { max: Infinity, status: "danger", label: "MAX LOAD" },
    ],
    maf: [
      { max: 150, status: "optimal", label: "NORMAL" },
      { max: 400, status: "warning", label: "HIGH" },
      { max: Infinity, status: "danger", label: "MAX FLOW" },
    ],
    fuel: [
      { max: 10,   status: "danger",  label: "CRITICAL LOW" },
      { max: 25,   status: "warning", label: "LOW" },
      { max: Infinity, status: "optimal", label: "OPTIMAL" },
    ],
    tire_fl: [
      { max: 25,   status: "danger",  label: "LOW DANGER" },
      { max: 30,   status: "warning", label: "UNDER-INFLATED" },
      { max: 35,   status: "optimal", label: "OPTIMAL" },
      { max: 40,   status: "warning", label: "OVER-INFLATED" },
      { max: Infinity, status: "danger", label: "HIGH DANGER" },
    ],
    tire_fr: [
      { max: 25,   status: "danger",  label: "LOW DANGER" },
      { max: 30,   status: "warning", label: "UNDER-INFLATED" },
      { max: 35,   status: "optimal", label: "OPTIMAL" },
      { max: 40,   status: "warning", label: "OVER-INFLATED" },
      { max: Infinity, status: "danger", label: "HIGH DANGER" },
    ],
    tire_rl: [
      { max: 25,   status: "danger",  label: "LOW DANGER" },
      { max: 30,   status: "warning", label: "UNDER-INFLATED" },
      { max: 35,   status: "optimal", label: "OPTIMAL" },
      { max: 40,   status: "warning", label: "OVER-INFLATED" },
      { max: Infinity, status: "danger", label: "HIGH DANGER" },
    ],
    tire_rr: [
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


  /* ── Gauge update ──────────────────────────────── */
  const STATUS_CLASSES = ["status-optimal", "status-warning", "status-danger", "status-cold"];

  function setGaugeValue(type, value) {
    const cfg = GAUGES[type];
    const clamped = Math.max(cfg.min, Math.min(cfg.max, value));
    const progress = (clamped - cfg.min) / (cfg.max - cfg.min);
    const pct = progress * 100;

    let cardClass;
    if (type === "psi") {
      cardClass = "psi";
    } else if (type.startsWith("tire_")) {
      cardClass = type.replace("_", "-");
    } else {
      cardClass = type;
    }
    
    const fill = $(`.gauge-card.${cardClass} .horiz-gauge-fill`);
    const num   = $(`.gauge-card.${cardClass} .gauge-number`);
    const badge = $(`.gauge-card.${cardClass} .status-badge`);

    if (fill) fill.style.width = pct + "%";
    if (num) {
      animateNumber(num, parseFloat(num.textContent) || 0, clamped, 400);
    }

    /* Apply status coloring */
    const st = getStatus(type, clamped);
    const cls = `status-${st.status}`;
    if (fill) { STATUS_CLASSES.forEach(c => fill.classList.remove(c)); fill.classList.add(cls); }
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
        setGaugeValue("rpm",   msg.data.engine_rpm);
        setGaugeValue("throttle", msg.data.throttle_pct);
        setGaugeValue("load", msg.data.engine_load_pct);
        setGaugeValue("maf", msg.data.maf_g_sec);
        setGaugeValue("oil",   msg.data.oil_pressure_psi);
        setGaugeValue("battery", msg.data.battery_voltage_v);
        setGaugeValue("fuel",  msg.data.fuel_level_pct);
        setGaugeValue("tire_fl", msg.data.tire_pressure_fl_psi);
        setGaugeValue("tire_fr", msg.data.tire_pressure_fr_psi);
        setGaugeValue("tire_rl", msg.data.tire_pressure_rl_psi);
        setGaugeValue("tire_rr", msg.data.tire_pressure_rr_psi);
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
    // Slider events
    $$("input[type='range']").forEach((slider) => {
      updateSliderFill(slider);
      slider.addEventListener("input", () => {
        const display = slider.closest(".gauge-card").querySelector(".slider-value-display");
        const cfg = GAUGES[slider.dataset.gauge];
        if (display && !display.querySelector("input")) {
          display.textContent = `${slider.value} ${cfg.unit}`;
        }
        updateSliderFill(slider);
        // Status badges update only from telemetry heartbeat, not local slider
      });
    });

    // Make value displays editable
    $$(".slider-value-display").forEach((display) => {
      display.style.cursor = "pointer";
      display.title = "Click to edit manually";
      
      display.addEventListener("click", function() {
        if (this.querySelector("input")) return;
        
        const card = this.closest(".gauge-card");
        const slider = card.querySelector("input[type='range']");
        const cfg = GAUGES[slider.dataset.gauge];
        
        const input = document.createElement("input");
        input.type = "number";
        input.value = slider.value;
        input.step = slider.step || "1";
        input.min = slider.min;
        input.max = slider.max;
        input.style.width = "60px";
        input.style.background = "rgba(0, 0, 0, 0.5)";
        input.style.color = "#00e5ff";
        input.style.border = "1px solid #00e5ff";
        input.style.borderRadius = "3px";
        input.style.padding = "2px 4px";
        input.style.fontFamily = "inherit";
        input.style.fontSize = "inherit";
        input.style.textAlign = "right";
        input.style.outline = "none";
        
        const unitSpan = document.createElement("span");
        unitSpan.textContent = " " + cfg.unit;
        
        this.innerHTML = "";
        this.appendChild(input);
        this.appendChild(unitSpan);
        
        input.focus();
        input.select();
        
        const applyValue = () => {
          let val = parseFloat(input.value);
          if (isNaN(val)) val = parseFloat(slider.value);
          val = Math.max(parseFloat(slider.min), Math.min(parseFloat(slider.max), val));
          slider.value = val;
          display.textContent = `${slider.value} ${cfg.unit}`;
          slider.dispatchEvent(new Event('input'));
          
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "update", parameter: cfg.param, value: val }));
          }
        };
        
        input.addEventListener("blur", applyValue);
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") {
            input.blur();
            // Trigger APPLY button click automatically
            const btnApply = card.querySelector(".btn-apply");
            if (btnApply) btnApply.click();
          }
        });
      });
    });

    // Apply buttons
    $$(".btn-apply").forEach((btn) => {
      btn.addEventListener("click", () => {
        const card = btn.closest(".gauge-card");
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

    // --- Auto-Drive Logic ---
    let isAutomated = false;
    let autoClock = 0;
    const btnAuto = document.getElementById("btn-auto-drive");
    const sliders = $$("input[type='range']");

    if (btnAuto) {
      btnAuto.addEventListener("click", () => {
        isAutomated = !isAutomated;
        btnAuto.textContent = `Toggle Auto-Drive: ${isAutomated ? "ON" : "OFF"}`;
        btnAuto.style.background = isAutomated ? "#00663a" : "#222";
        
        // Send toggle_auto_drive action to backend
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "toggle_auto_drive" }));
        }
        
        sliders.forEach(s => {
          s.disabled = isAutomated;
          s.style.opacity = isAutomated ? "0.5" : "1";
        });
        
        if (isAutomated) {
          autoClock = 0;
        }
      });
    }

    setInterval(() => {
      if (!isAutomated) return;

      // 90-second driving cycle with highway phases
      let tSpeed = 0, tRpm = 800, tThrottle = 0, tLoad = 15, tMaf = 4, tTemp = 90;
      
      if (autoClock >= 0 && autoClock <= 10) {
        // Seconds 0-10: Idling
        tSpeed = 0; tRpm = 800; tThrottle = 0; tLoad = 15; tMaf = 4;
      } else if (autoClock >= 11 && autoClock <= 25) {
        // Seconds 11-25: City Acceleration
        tSpeed = 60; tRpm = 3000; tThrottle = 40; tLoad = 60; tMaf = 35;
      } else if (autoClock >= 26 && autoClock <= 40) {
        // Seconds 26-40: City Cruising
        tSpeed = 60; tRpm = 2000; tThrottle = 15; tLoad = 30; tMaf = 20;
      } else if (autoClock >= 41 && autoClock <= 55) {
        // Seconds 41-55: Highway Acceleration
        tSpeed = 130; tRpm = 4000; tThrottle = 65; tLoad = 85; tMaf = 60;
      } else if (autoClock >= 56 && autoClock <= 75) {
        // Seconds 56-75: Highway Cruising
        tSpeed = 130; tRpm = 2800; tThrottle = 25; tLoad = 45; tMaf = 40;
      } else if (autoClock >= 76 && autoClock <= 90) {
        // Seconds 76-90: Deceleration
        tSpeed = 0; tRpm = 800; tThrottle = 0; tLoad = 0; tMaf = 4;
      }

      const targets = {
        speed: tSpeed,
        rpm: tRpm,
        throttle: tThrottle,
        load: tLoad,
        maf: tMaf,
        temp: tTemp,
        tire_fl: 32,
        tire_fr: 32,
        tire_rl: 32,
        tire_rr: 32,
        battery: 14.2,
        oil: 40
      };

      const bulkData = {};
      bulkData["tire_pressure_psi"] = 32.0; // fallback for rule engine

      sliders.forEach(slider => {
        const gauge = slider.dataset.gauge;
        let current = parseFloat(slider.value);
        
        if (gauge === 'fuel') {
          current = Math.max(0, current - 0.01);
        } else if (targets[gauge] !== undefined) {
          current = current + (targets[gauge] - current) * 0.15;
        }
        
        slider.value = current;
        slider.dispatchEvent(new Event('input'));
        
        const cfg = GAUGES[gauge];
        if (cfg && cfg.param) {
          bulkData[cfg.param] = current;
        }
      });

      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "bulk_update", data: bulkData }));
      }

      autoClock++;
      if (autoClock > 90) {
        autoClock = 0;
      }
    }, 1000);
  });

  /* ── Slider status coloring ────────────────────── */
  function updateSliderStatus(slider) {
    const gauge = slider.dataset.gauge;
    const val = parseFloat(slider.value);
    const st = getStatus(gauge, val);
    const display = slider.closest(".gauge-card").querySelector(".slider-value-display");
    if (display) {
      STATUS_CLASSES.forEach(c => display.classList.remove(c));
      display.classList.add(`status-${st.status}`);
    }
  }
})();
