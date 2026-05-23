/* ── Premium High-End Animated Automotive Background ─────────────────
   Renders a stunning, aggressive, state-of-the-art cyber-performance background:
   • High-contrast 3D Perspective Racing Highway / Grid moving at high speed
   • Aerodynamic wind tunnel flow streaks (flowing bright neon light trails)
   • Glowing HUD telemetry components (rotating neon dial outlines and tech markers)
   • Rich, highly visible colored nebulae pulsing dynamically (Red, Cyan, Green, Purple)
   • Sleek carbon-fiber metallic texture overlays
   ─────────────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  /* ── Resize handling ───────────────────────────── */
  let W, H;
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  /* ── Colors (Increased alpha for high visibility & aggression) ── */
  const CYAN   = "rgba(0, 200, 255, 0.55)";
  const RED    = "rgba(255, 45, 85, 0.55)";
  const GREEN  = "rgba(0, 230, 118, 0.45)";
  const AMBER  = "rgba(255, 171, 0, 0.45)";
  const PURPLE = "rgba(170, 0, 255, 0.35)";

  /* ── State variables ───────────────────────────── */
  let speedFactor = 1.0; // Dynamic multiplier based on simulation
  let time = 0;

  // 3D Perspective Grid
  let gridOffset = 0;

  // Aerodynamic Streaks (High-speed bright flow lines)
  const STREAK_COUNT = 50;
  const streaks = [];
  function createStreak(initial = false) {
    return {
      x: initial ? Math.random() * W : -200,
      y: Math.random() * H * 0.9, // distributed across height
      len: 120 + Math.random() * 250,
      speed: 6 + Math.random() * 12,
      width: 1.5 + Math.random() * 3,
      color: Math.random() > 0.5 ? "rgba(0, 229, 255, " : "rgba(255, 45, 85, ",
      alpha: 0.35 + Math.random() * 0.45
    };
  }
  for (let i = 0; i < STREAK_COUNT; i++) {
    streaks.push(createStreak(true));
  }

  // Floating Nano Particles
  const PARTICLE_COUNT = 45;
  const particles = [];
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.7,
      vy: (Math.random() - 0.5) * 0.7,
      r: 2 + Math.random() * 2.5,
      alpha: 0.3 + Math.random() * 0.5,
      glow: Math.random() > 0.5 ? "rgba(0, 229, 255, 0.85)" : "rgba(255, 45, 85, 0.85)"
    });
  }

  // HUD Tech Elements (highly visible in background)
  const hudElements = [
    { cx: 0.12 * W, cy: 0.3 * H, r: 140, spinSpeed: 0.003, angle: 0, scale: 1 },
    { cx: 0.88 * W, cy: 0.4 * H, r: 180, spinSpeed: -0.002, angle: Math.PI / 4, scale: 0.8 },
    { cx: 0.15 * W, cy: 0.75 * H, r: 100, spinSpeed: 0.004, angle: Math.PI, scale: 1.25 }
  ];

  /* ── Update state based on active speed baseline ─ */
  function updateSpeedFactor() {
    const speedDisplay = document.querySelector(".ctrl-speed .slider-value-display");
    if (speedDisplay) {
      const parsedVal = parseInt(speedDisplay.textContent, 10);
      if (!isNaN(parsedVal)) {
        speedFactor = 0.3 + (parsedVal / 300) * 3.5;
      }
    }
  }

  /* ── Rendering Functions ───────────────────────── */

  // Sleek Carbon Fiber Grid Lines
  function drawCarbonGrid() {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.025)";
    ctx.lineWidth = 1.2;
    const spacing = 18;
    for (let x = -H; x < W; x += spacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x + H, H);
      ctx.stroke();
    }
  }

  // 3D Perspective Racing Highway
  function draw3DGrid() {
    const horizon = H * 0.42; // Horizon point
    const gridHeight = H - horizon;
    
    gridOffset = (gridOffset + 4.5 * speedFactor) % 65;

    // Highway surface gradient
    const grad = ctx.createLinearGradient(0, horizon, 0, H);
    grad.addColorStop(0, "rgba(5, 5, 12, 0.98)");
    grad.addColorStop(0.35, "rgba(8, 14, 38, 0.85)");
    grad.addColorStop(1, "rgba(24, 8, 40, 0.92)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, horizon, W, gridHeight);

    // Horizon Neon Line (extremely sharp and glowing)
    ctx.shadowColor = "rgba(0, 229, 255, 0.8)";
    ctx.shadowBlur = 12;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.45)";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(0, horizon);
    ctx.lineTo(W, horizon);
    ctx.stroke();
    ctx.shadowBlur = 0; // reset shadow

    const centerX = W * 0.5;

    // Perspective Lanes (highly visible)
    ctx.strokeStyle = "rgba(0, 229, 255, 0.16)";
    ctx.lineWidth = 1.8;
    const lineCount = 18;
    for (let i = -lineCount; i <= lineCount; i++) {
      const targetX = centerX + i * 180;
      ctx.beginPath();
      ctx.moveTo(centerX, horizon);
      ctx.lineTo(targetX, H);
      ctx.stroke();
    }

    // Horizontal Depth Lines (highly visible moving forward)
    ctx.strokeStyle = "rgba(255, 45, 85, 0.22)";
    for (let yOffset = gridOffset; yOffset < gridHeight; yOffset += 50) {
      const normY = yOffset / gridHeight;
      const actualY = horizon + Math.pow(normY, 2) * gridHeight;
      ctx.lineWidth = 0.6 + normY * 3.5;
      ctx.beginPath();
      ctx.moveTo(0, actualY);
      ctx.lineTo(W, actualY);
      ctx.stroke();
    }
    
    // Racing Outer Guardrails (Aggressive double glowing bars)
    // Left Guardrail
    ctx.shadowColor = "rgba(0, 229, 255, 0.8)";
    ctx.shadowBlur = 15;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.5)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(centerX, horizon);
    ctx.lineTo(centerX - 680, H);
    ctx.stroke();

    ctx.strokeStyle = "rgba(0, 229, 255, 0.25)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX, horizon);
    ctx.lineTo(centerX - 700, H);
    ctx.stroke();

    // Right Guardrail
    ctx.shadowColor = "rgba(255, 45, 85, 0.8)";
    ctx.shadowBlur = 15;
    ctx.strokeStyle = "rgba(255, 45, 85, 0.5)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(centerX, horizon);
    ctx.lineTo(centerX + 680, H);
    ctx.stroke();

    ctx.strokeStyle = "rgba(255, 45, 85, 0.25)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(centerX, horizon);
    ctx.lineTo(centerX + 700, H);
    ctx.stroke();

    ctx.shadowBlur = 0; // reset
  }

  // Aerodynamic Wind Streaks (flowing neon light trails)
  function drawAerodynamics() {
    for (let i = 0; i < STREAK_COUNT; i++) {
      const s = streaks[i];
      s.x += s.speed * speedFactor;

      if (s.x > W) {
        streaks[i] = createStreak();
      }

      ctx.beginPath();
      const grad = ctx.createLinearGradient(s.x, s.y, s.x + s.len, s.y);
      grad.addColorStop(0, "rgba(255,255,255,0)");
      grad.addColorStop(0.5, `${s.color}${s.alpha})`);
      grad.addColorStop(1, "rgba(255,255,255,0)");

      ctx.strokeStyle = grad;
      ctx.lineWidth = s.width;
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(s.x + s.len, s.y);
      ctx.stroke();
    }
  }

  // Tech HUD Background Elements (increased alpha for matching dashboard tech)
  function drawHUD() {
    hudElements[0].cx = 0.12 * W;
    hudElements[0].cy = 0.3 * H;
    hudElements[1].cx = 0.88 * W;
    hudElements[1].cy = 0.4 * H;
    hudElements[2].cx = 0.15 * W;
    hudElements[2].cy = 0.75 * H;

    hudElements.forEach((hud) => {
      hud.angle += hud.spinSpeed * speedFactor;
      ctx.save();
      ctx.translate(hud.cx, hud.cy);
      ctx.scale(hud.scale, hud.scale);

      // Rotating dashed outer dial
      ctx.strokeStyle = "rgba(0, 229, 255, 0.18)";
      ctx.lineWidth = 1.8;
      ctx.setLineDash([10, 15]);
      ctx.beginPath();
      ctx.arc(0, 0, hud.r, 0, Math.PI * 2);
      ctx.stroke();

      // Rotating solid segments
      ctx.strokeStyle = "rgba(255, 45, 85, 0.15)";
      ctx.lineWidth = 3.5;
      ctx.setLineDash([50, 100]);
      ctx.rotate(hud.angle);
      ctx.beginPath();
      ctx.arc(0, 0, hud.r - 15, 0, Math.PI * 2);
      ctx.stroke();

      // Target Crosshairs
      ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
      ctx.lineWidth = 1.2;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(-hud.r - 25, 0); ctx.lineTo(hud.r + 25, 0);
      ctx.moveTo(0, -hud.r - 25); ctx.lineTo(0, hud.r + 25);
      ctx.stroke();

      ctx.restore();
    });
  }

  // Floating Nano Particles
  function drawParticles() {
    particles.forEach((p) => {
      p.x += p.vx * speedFactor;
      p.y += p.vy * speedFactor;

      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;

      // Draw glowing particle cloud
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 4.5, 0, Math.PI * 2);
      ctx.fillStyle = p.glow;
      ctx.globalAlpha = p.alpha * 0.45;
      ctx.fill();

      // Draw particle core
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.globalAlpha = p.alpha * 0.9;
      ctx.fill();
    });
    ctx.globalAlpha = 1.0;
  }

  // Large Ambient Atmospheric Nebulae Glow
  function drawNebulae() {
    const glows = [
      { x: W * 0.1, y: H * 0.15, r: Math.max(W, H) * 0.38, c: CYAN },
      { x: W * 0.9, y: H * 0.22, r: Math.max(W, H) * 0.35, c: RED },
      { x: W * 0.25, y: H * 0.85, r: Math.max(W, H) * 0.32, c: PURPLE },
      { x: W * 0.75, y: H * 0.72, r: Math.max(W, H) * 0.34, c: GREEN }
    ];

    glows.forEach((g) => {
      const pulse = 1.0 + 0.18 * Math.sin(time * 0.018);
      const rad = g.r * pulse;
      const grad = ctx.createRadialGradient(g.x, g.y, 0, g.x, g.y, rad);
      grad.addColorStop(0, g.c);
      grad.addColorStop(0.5, g.c.replace("0.55", "0.22").replace("0.45", "0.18").replace("0.35", "0.12"));
      grad.addColorStop(1, "rgba(0,0,0,0)");
      
      ctx.fillStyle = grad;
      ctx.fillRect(g.x - rad, g.y - rad, rad * 2, rad * 2);
    });
  }

  // Aggressive dark vignette border for high contrast
  function drawVignette() {
    const grad = ctx.createRadialGradient(W / 2, H / 2, W * 0.28, W / 2, H / 2, W * 0.8);
    grad.addColorStop(0, "rgba(4, 4, 10, 0)");
    grad.addColorStop(0.6, "rgba(4, 4, 10, 0.45)");
    grad.addColorStop(1, "rgba(2, 2, 6, 0.96)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
  }

  /* ── Master loop ───────────────────────────────── */
  function tick() {
    time++;
    updateSpeedFactor();
    
    // Clear screen with deep motorsport carbon black
    ctx.fillStyle = "#030308";
    ctx.fillRect(0, 0, W, H);

    // Composite components
    drawCarbonGrid();
    drawNebulae();
    draw3DGrid();
    drawHUD();
    drawAerodynamics();
    drawParticles();
    drawVignette();

    requestAnimationFrame(tick);
  }

  // Initialize
  tick();
})();
