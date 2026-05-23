/* ── Vehicle Health Analysis Dashboard ─────────────────────────── */
(function () {
  "use strict";

  /* ── DOM refs ──────────────────────────────────── */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const connDot = $(".conn-dot");
  const connLabel = $(".conn-label");
  const alertsContainer = $(".alerts-container");
  const btnExportCsv = $("#btn-export-csv");

  /* ── Data buffers for charts ───────────────────── */
  const chartData = {
    speed: [],
    temp: [],
    psi: [],
  };

  const MAX_CHART_POINTS = 60;

  /* ── WebSocket connection ──────────────────────── */
  let ws;
  let reconnectTimer;
  let messageCount = 0;

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/data-analysis`;
    console.log("🔌 Connecting to:", url);
    
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log("✅ WebSocket OPEN");
      connDot.classList.add("connected");
      connLabel.textContent = "CONNECTED";
      messageCount = 0;
    };

    ws.onclose = () => {
      console.log("❌ WebSocket CLOSED");
      connDot.classList.remove("connected");
      connLabel.textContent = "DISCONNECTED";
      clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error("❌ WebSocket ERROR:", error);
      ws.close();
    };

    ws.onmessage = (e) => {
      messageCount++;
      console.log(`📨 Message #${messageCount}:`, e.data.substring(0, 100));
      
      let msg;
      try {
        msg = JSON.parse(e.data);
      } catch (err) {
        console.error("❌ JSON parse error:", err);
        return;
      }

      console.log("📊 Message type:", msg.type);

      if (msg.type === "analysis" && msg.data) {
        console.log("✅ Processing analysis data");
        updateAnalysisDashboard(msg.data);
      } else if (msg.type === "summary") {
        console.log("✅ Processing summary data");
        updateSessionSummary(msg.data);
      } else {
        console.warn("⚠️ Unknown message type:", msg.type);
      }
    };
  }

  /* ── Update dashboard with analysis data ────────── */
  function updateAnalysisDashboard(analysis) {
    console.log("🔄 Updating dashboard with:", analysis);
    
    // analysis is already the full analysis_result object from the broadcaster
    if (!analysis || !analysis.current_values) {
      console.error("❌ Invalid analysis object:", analysis);
      return;
    }

    console.log("📈 Current values:", analysis.current_values);
    console.log("📊 Health score:", analysis.health_score);

    // Update health score
    updateHealthScore(analysis.health_score);

    // Update metrics
    updateMetrics(analysis.current_values, analysis.status, analysis.trends);

    // Update alerts
    updateAlerts(analysis.alerts);

    // Update charts
    updateCharts(analysis.current_values);

    // Update session stats
    updateSessionStats(analysis.window_size);
    
    console.log("✅ Dashboard updated successfully");
  }

  /* ── Health Score Update ───────────────────────── */
  function updateHealthScore(healthScore) {
    const score = healthScore.score;
    const status = healthScore.status;

    // Update score display
    const healthNumber = $(".health-number");
    const healthStatus = $(".health-status");
    const healthArc = $(".health-value-arc");

    if (healthNumber) {
      animateNumber(healthNumber, parseFloat(healthNumber.textContent) || 0, score, 600);
    }

    if (healthStatus) {
      healthStatus.textContent = status;
      healthStatus.className = `health-status status-${getStatusClass(status)}`;
    }

    // Update arc
    if (healthArc) {
      const progress = score / 100;
      const offset = 424.12 * (1 - progress);
      healthArc.style.strokeDashoffset = offset;
    }

    // Update component scores
    const componentScores = healthScore.component_scores;
    updateComponentBar(".comp-fill.speed-fill", componentScores.speed);
    updateComponentBar(".comp-fill.temp-fill", componentScores.temperature);
    updateComponentBar(".comp-fill.psi-fill", componentScores.tire_pressure);
  }

  function updateComponentBar(selector, score) {
    const bar = $(selector);
    if (bar) {
      bar.style.width = score + "%";
    }
  }

  function getStatusClass(status) {
    if (status === "EXCELLENT") return "optimal";
    if (status === "GOOD") return "optimal";
    if (status === "FAIR") return "warning";
    return "danger";
  }

  /* ── Metrics Update ────────────────────────────── */
  function updateMetrics(values, status, trends) {
    updateMetricCard("speed", values.speed_kmh, status.speed, trends.speed);
    updateMetricCard("temp", values.engine_temp_c, status.temp, trends.temp);
    updateMetricCard("psi", values.tire_pressure_psi, status.psi, trends.psi);
  }

  function updateMetricCard(type, value, status, trend) {
    const card = $(`.metric-card.${type}-metric`);
    if (!card) return;

    // Update value
    const metricValue = card.querySelector(".metric-value");
    if (metricValue) {
      const unit = type === "speed" ? " km/h" : type === "temp" ? " °C" : " PSI";
      metricValue.textContent = value.toFixed(1) + unit;
    }

    // Update status badge
    const statusBadge = card.querySelector(".metric-status");
    if (statusBadge) {
      statusBadge.textContent = status.toUpperCase();
      statusBadge.className = `metric-status status-${status}`;
    }

    // Update details
    updateDetailValue(card, ".current-" + type, value.toFixed(1));
    updateDetailValue(card, ".trend-" + type, trend.direction);
  }

  function updateDetailValue(card, selector, value) {
    const el = card.querySelector(selector);
    if (el) {
      el.textContent = value;
    }
  }

  /* ── Alerts Update ─────────────────────────────── */
  function updateAlerts(alerts) {
    const alertCount = $(".alert-count");
    if (alertCount) {
      alertCount.textContent = alerts.length;
    }

    // Clear existing alerts
    const existingAlerts = $$(".alert-item");
    existingAlerts.forEach((alert) => alert.remove());

    if (alerts.length === 0) {
      const placeholder = $(".alert-placeholder");
      if (placeholder) {
        placeholder.style.display = "block";
      }
      return;
    }

    const placeholder = $(".alert-placeholder");
    if (placeholder) {
      placeholder.style.display = "none";
    }

    // Add new alerts
    alerts.forEach((alert) => {
      const alertEl = document.createElement("div");
      alertEl.className = "alert-item " + getAlertSeverity(alert);
      alertEl.textContent = alert;
      alertsContainer.appendChild(alertEl);
    });

    // Keep only last 10 alerts
    const allAlerts = $$(".alert-item");
    if (allAlerts.length > 10) {
      for (let i = 0; i < allAlerts.length - 10; i++) {
        allAlerts[i].remove();
      }
    }

    alertsContainer.scrollTop = alertsContainer.scrollHeight;
  }

  function getAlertSeverity(alert) {
    if (alert.includes("CRITICAL") || alert.includes("DANGER") || alert.includes("EXCESSIVE")) {
      return "danger";
    } else if (alert.includes("HIGH") || alert.includes("RAPID") || alert.includes("LEAK")) {
      return "warning";
    }
    return "info";
  }

  /* ── Charts Update ─────────────────────────────── */
  function updateCharts(values) {
    chartData.speed.push(values.speed_kmh);
    chartData.temp.push(values.engine_temp_c);
    chartData.psi.push(values.tire_pressure_psi);

    // Keep only last 60 points
    if (chartData.speed.length > MAX_CHART_POINTS) {
      chartData.speed.shift();
      chartData.temp.shift();
      chartData.psi.shift();
    }

    // Draw charts
    drawChart("chart-speed", chartData.speed, "Speed (km/h)", "#00b4ff");
    drawChart("chart-temp", chartData.temp, "Temperature (°C)", "#ff6b35");
    drawChart("chart-psi", chartData.psi, "Tire Pressure (PSI)", "#00e676");
  }

  function drawChart(canvasId, data, label, color) {
    const canvas = $(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
    ctx.fillRect(0, 0, width, height);

    if (data.length < 2) return;

    // Find min/max
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Draw grid lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Draw line chart
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = (width / (data.length - 1 || 1)) * i;
      const normalized = (data[i] - min) / range;
      const y = height - normalized * height * 0.8 - height * 0.1;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Draw points
    ctx.fillStyle = color;
    for (let i = 0; i < data.length; i++) {
      const x = (width / (data.length - 1 || 1)) * i;
      const normalized = (data[i] - min) / range;
      const y = height - normalized * height * 0.8 - height * 0.1;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    }

    // Draw labels
    ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
    ctx.font = "11px 'Rajdhani', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(min.toFixed(1), width * 0.05, height - 5);
    ctx.fillText(max.toFixed(1), width * 0.05, 15);
  }

  /* ── Session Stats Update ──────────────────────── */
  function updateSessionStats(windowSize) {
    const dataPoints = $(".data-points");
    if (dataPoints) {
      dataPoints.textContent = windowSize;
    }

    const sessionDuration = $(".session-duration");
    if (sessionDuration) {
      // Calculate duration from window size (1 reading per second)
      sessionDuration.textContent = windowSize + "s";
    }
  }

  function updateSessionSummary(summary) {
    if (summary.status === "NO_DATA") return;

    // Update average values in metric cards
    updateDetailValue(
      $(".metric-card.speed-metric"),
      ".avg-speed",
      summary.speed.avg.toFixed(1)
    );
    updateDetailValue(
      $(".metric-card.temp-metric"),
      ".avg-temp",
      summary.temperature.avg.toFixed(1)
    );
    updateDetailValue(
      $(".metric-card.psi-metric"),
      ".avg-psi",
      summary.tire_pressure.avg.toFixed(1)
    );
  }

  /* ── Smooth number animation ───────────────────── */
  function animateNumber(el, from, to, duration) {
    const start = performance.now();
    const decimals = to % 1 !== 0 ? 1 : 0;

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3); // ease-out cubic
      const cur = from + (to - from) * ease;
      el.textContent = cur.toFixed(decimals);
      if (t < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  /* ── CSV Export ────────────────────────────────── */
  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "get_summary" }));
        btnExportCsv.textContent = "EXPORTING...";
        setTimeout(() => {
          btnExportCsv.textContent = "Download";
        }, 1500);
      }
    });
  }

  /* ── Init ──────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    connect();

    // Request initial summary
    setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "get_summary" }));
      }
    }, 500);
  });
})();
