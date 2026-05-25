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

  /* ── Session tracking ──────────────────────────── */
  let sessionStartTime = Date.now();
  let lastContradictions = [];

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
    console.log("🚨 Contradictions:", analysis.health_score.contradictions);

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
    
    // Get contradictions from health_score
    const contradictions = analysis.health_score.contradictions || [];
    
    // Display contradictions if any
    if (contradictions.length > 0) {
      console.log("🚨 Displaying contradictions:", contradictions);
      displayContradictions(contradictions);
    } else {
      // Clear contradictions if none
      console.log("✅ Clearing contradictions");
      displayContradictions([]);
    }
    
    // Update service recommendation
    console.log("🔧 Updating service recommendation with:", { score: analysis.health_score.score, contradictions });
    updateServiceRecommendation(analysis.health_score, contradictions);
    
    // Display physics metrics
    if (analysis.health_score.tire_speed_risk !== undefined) {
      displayPhysicsMetrics(analysis.health_score);
    }
    
    console.log("✅ Dashboard updated successfully");
  }

  /* ── Health Score Update ───────────────────────── */
  function updateHealthScore(healthScore) {
    const score = healthScore.score;
    const status = healthScore.status;
    const isEmergency = healthScore.emergency || false;

    // Update score display
    const healthNumber = $(".health-number");
    const healthStatus = $(".health-status");
    const healthArc = $(".health-value-arc");

    if (healthNumber) {
      animateNumber(healthNumber, parseFloat(healthNumber.textContent) || 0, score, 600);
    }

    if (healthStatus) {
      healthStatus.textContent = status;
      
      // Apply emergency styling
      if (isEmergency) {
        healthStatus.className = `health-status status-emergency`;
        // Add pulsing animation for emergency
        healthStatus.style.animation = "pulse 0.5s infinite";
      } else {
        healthStatus.className = `health-status status-${getStatusClass(status)}`;
        healthStatus.style.animation = "none";
      }
    }

    // Update arc with emergency color
    if (healthArc) {
      const progress = score / 100;
      const offset = 424.12 * (1 - progress);
      healthArc.style.strokeDashoffset = offset;
      
      if (isEmergency) {
        healthArc.style.stroke = "#ff0000";
      } else {
        healthArc.style.stroke = getArcColor(score);
      }
    }

    // Update component scores
    const componentScores = healthScore.component_scores;
    updateComponentBar(".comp-fill.speed-fill", componentScores.speed);
    updateComponentBar(".comp-fill.temp-fill", componentScores.temperature);
    updateComponentBar(".comp-fill.psi-fill", componentScores.tire_pressure);
    
    // Display physics metrics
    if (healthScore.tire_speed_risk !== undefined) {
      displayPhysicsMetrics(healthScore);
    }
  }

  function getArcColor(score) {
    if (score >= 80) return "#00ff00";
    if (score >= 60) return "#00b4ff";
    if (score >= 40) return "#ffaa00";
    return "#ff6b35";
  }

  function displayContradictions(contradictions) {
    // Only show contradictions if they're different from last time
    const contradictionStr = JSON.stringify(contradictions);
    const lastStr = JSON.stringify(lastContradictions);
    
    if (contradictionStr === lastStr && contradictions.length > 0) {
      // Same contradictions, don't update
      return;
    }
    
    lastContradictions = contradictions;
    
    // If no contradictions, remove the container
    if (contradictions.length === 0) {
      const existingContainer = document.querySelector(".contradictions-container");
      if (existingContainer) {
        existingContainer.style.animation = "slide-up 0.3s ease-out";
        setTimeout(() => existingContainer.remove(), 300);
      }
      return;
    }
    
    // Remove old container if exists
    const oldContainer = document.querySelector(".contradictions-container");
    if (oldContainer) {
      oldContainer.remove();
    }
    
    // Create new container
    const container = document.createElement("div");
    container.className = "contradictions-container";
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: rgba(255, 0, 0, 0.9);
      border: 2px solid #ff0000;
      border-radius: 8px;
      padding: 15px;
      max-width: 400px;
      z-index: 10000;
      font-family: 'Rajdhani', monospace;
      color: #fff;
      box-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
      animation: slide-down 0.4s ease-out;
    `;
    
    container.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">
        🚨 SYSTEM CONTRADICTIONS DETECTED
      </div>
      ${contradictions.map(c => `<div style="font-size: 12px; margin: 5px 0;">• ${c}</div>`).join("")}
    `;
    
    document.body.appendChild(container);
  }

  function displayPhysicsMetrics(healthScore) {
    const physicsContainer = document.querySelector(".physics-metrics");
    if (!physicsContainer) return;
    
    const tireSpeedRisk = healthScore.tire_speed_risk || 0;
    const tempPenalty = healthScore.temp_correlation_penalty || 0;
    
    let riskLevel = "LOW";
    if (tireSpeedRisk > 70) riskLevel = "CRITICAL";
    else if (tireSpeedRisk > 40) riskLevel = "HIGH";
    else if (tireSpeedRisk > 20) riskLevel = "MODERATE";
    
    physicsContainer.innerHTML = `
      <div style="font-size: 11px; color: #00b4ff; margin-top: 10px;">
        <div>Tire-Speed Risk: ${tireSpeedRisk}% (${riskLevel})</div>
        <div>Temp Correlation Penalty: ${tempPenalty.toFixed(1)}°</div>
      </div>
    `;
  }

  function updateComponentBar(selector, score) {
    const bar = $(selector);
    if (bar) {
      bar.style.width = score + "%";
    }
  }

  function getStatusClass(status) {
    if (status.includes("EMERGENCY")) return "emergency";
    if (status.includes("EXCELLENT")) return "optimal";
    if (status.includes("GOOD")) return "optimal";
    if (status.includes("FAIR")) return "warning";
    if (status.includes("CRITICAL")) return "danger";
    return "warning";
  }

  /* ── Metrics Update ────────────────────────────── */
  function updateMetrics(values, status, trends) {
    updateMetricCard("speed", values.speed_kmh, status.speed, trends.speed, "km/h");
    updateMetricCard("temp", values.engine_temp_c, status.temp, trends.temp, "°C");
    updateMetricCard("psi", values.tire_pressure_psi, status.psi, trends.psi, "PSI");
    updateMetricCard("rpm", values.engine_rpm, status.rpm, null, "RPM");
    updateMetricCard("oil", values.oil_pressure_psi, status.oil, null, "PSI");
    updateMetricCard("battery", values.battery_voltage_v, status.battery, null, "V");
  }

  function updateMetricCard(type, value, status, trend, unit) {
    const card = $(`.metric-card.${type}-metric`);
    if (!card) {
      console.error(`❌ Card not found for type: ${type}`);
      return;
    }

    console.log(`📊 Updating ${type} metric:`, { value, status, trend });

    // Update value
    const metricValue = card.querySelector(".metric-value");
    if (metricValue) {
      metricValue.textContent = value.toFixed(1) + " " + unit;
      console.log(`✅ ${type} value updated:`, metricValue.textContent);
    } else {
      console.error(`❌ metric-value not found for ${type}`);
    }

    // Update status badge
    const statusBadge = card.querySelector(".metric-status");
    if (statusBadge) {
      statusBadge.textContent = status.toUpperCase();
      statusBadge.className = `metric-status status-${status}`;
      console.log(`✅ ${type} status updated:`, status);
    } else {
      console.error(`❌ metric-status not found for ${type}`);
    }

    // Update details
    updateDetailValue(card, ".current-" + type, value.toFixed(1));
    
    // Update trend if available
    if (trend) {
      updateDetailValue(card, ".trend-" + type, trend.direction);
    } else {
      // For new metrics without trends, show status
      updateDetailValue(card, "." + type + "-status", status.toUpperCase());
    }
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
      // Calculate actual duration from session start time
      const elapsedSeconds = Math.floor((Date.now() - sessionStartTime) / 1000);
      const minutes = Math.floor(elapsedSeconds / 60);
      const seconds = elapsedSeconds % 60;
      
      if (minutes > 0) {
        sessionDuration.textContent = `${minutes}m ${seconds}s`;
      } else {
        sessionDuration.textContent = `${seconds}s`;
      }
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

  /* ── Service Center Recommendation ─────────────── */
  function updateServiceRecommendation(healthScore, contradictions) {
    const recommendationStatus = $(".recommendation-status");
    const recommendationIcon = $(".recommendation-icon");
    const recommendationText = $(".recommendation-text");
    const recommendationHealth = $(".recommendation-health");
    const recommendationCritical = $(".recommendation-critical");
    const recommendationAction = $(".recommendation-action");
    
    if (!recommendationStatus) {
      console.error("❌ Recommendation status element not found");
      return;
    }
    
    const score = healthScore.score || 0;
    const status = healthScore.status || "UNKNOWN";
    const isEmergency = healthScore.emergency === true;
    
    console.log("🔧 Updating recommendation:", { score, status, isEmergency, contradictions });
    
    // Determine recommendation based on health score and contradictions
    let icon, text, action, criticalCount;
    
    if (isEmergency || contradictions.length > 0) {
      icon = "🚨";
      text = "IMMEDIATE SERVICE REQUIRED";
      action = "⚠️ STOP VEHICLE - Take to service center immediately";
      recommendationStatus.className = "recommendation-status status-emergency";
      criticalCount = contradictions.length > 0 ? contradictions.length : 1;
      console.log("✅ Set to EMERGENCY");
    } else if (score < 30) {
      icon = "🔴";
      text = "CRITICAL - Service required soon";
      action = "⚠️ Reduce speed and proceed to nearest service center";
      recommendationStatus.className = "recommendation-status status-critical";
      criticalCount = 1;
      console.log("✅ Set to CRITICAL");
    } else if (score < 60) {
      icon = "🟡";
      text = "WARNING - Schedule service";
      action = "⚠️ Schedule service within 24 hours";
      recommendationStatus.className = "recommendation-status status-warning";
      criticalCount = 0;
      console.log("✅ Set to WARNING");
    } else if (score < 80) {
      icon = "🟢";
      text = "GOOD - Routine maintenance recommended";
      action = "✅ Continue journey, schedule routine maintenance";
      recommendationStatus.className = "recommendation-status status-good";
      criticalCount = 0;
      console.log("✅ Set to GOOD");
    } else {
      icon = "✅";
      text = "EXCELLENT - Vehicle is safe";
      action = "✅ Continue journey safely";
      recommendationStatus.className = "recommendation-status status-excellent";
      criticalCount = 0;
      console.log("✅ Set to EXCELLENT");
    }
    
    if (recommendationIcon) {
      recommendationIcon.textContent = icon;
      console.log("✅ Icon updated:", icon);
    }
    if (recommendationText) {
      recommendationText.textContent = text;
      console.log("✅ Text updated:", text);
    }
    if (recommendationHealth) {
      recommendationHealth.textContent = `${score.toFixed(1)}/100 (${status})`;
      console.log("✅ Health updated:", recommendationHealth.textContent);
    }
    if (recommendationCritical) {
      if (criticalCount === 0) {
        recommendationCritical.textContent = "None";
        recommendationCritical.style.color = "#69f0ae";
      } else {
        recommendationCritical.textContent = `${criticalCount} issue${criticalCount > 1 ? 's' : ''}`;
        recommendationCritical.style.color = "#ff5577";
      }
      console.log("✅ Critical count updated:", recommendationCritical.textContent);
    }
    if (recommendationAction) {
      recommendationAction.textContent = action;
      console.log("✅ Action updated:", action);
    }
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
        
        // Show download info
        const originalText = btnExportCsv.textContent;
        btnExportCsv.textContent = "EXPORTING...";
        
        // Create and show download info
        showDownloadInfo();
        
        setTimeout(() => {
          btnExportCsv.textContent = originalText;
        }, 2000);
      } else {
        alert("WebSocket not connected. Please refresh the page.");
      }
    });
  }

  function showDownloadInfo() {
    // Remove old info if exists
    const oldInfo = document.querySelector(".download-info");
    if (oldInfo) oldInfo.remove();
    
    const info = document.createElement("div");
    info.className = "download-info";
    info.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: rgba(0, 230, 118, 0.15);
      border: 2px solid rgba(0, 230, 118, 0.5);
      border-radius: 8px;
      padding: 15px;
      max-width: 350px;
      z-index: 9999;
      font-family: 'Rajdhani', monospace;
      color: #69f0ae;
      box-shadow: 0 0 20px rgba(0, 230, 118, 0.3);
      animation: slide-up 0.4s ease-out;
    `;
    
    const timestamp = new Date().toLocaleString();
    info.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 10px; font-size: 13px;">
        ✅ CSV EXPORT READY
      </div>
      <div style="font-size: 11px; line-height: 1.6;">
        <div><strong>File:</strong> analysis_[timestamp].csv</div>
        <div><strong>Location:</strong> /data/ directory</div>
        <div><strong>Server Path:</strong> /home/rishon-pravin/Desktop/telemetry-dashboard/data/</div>
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0, 230, 118, 0.3);">
          <strong>Access via:</strong>
          <div>• Browser: Download folder</div>
          <div>• Terminal: cd data/ && ls -la</div>
        </div>
      </div>
    `;
    
    document.body.appendChild(info);
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
      info.style.animation = "slide-down 0.3s ease-out";
      setTimeout(() => info.remove(), 300);
    }, 8000);
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
