/* Add an animated block extrusion to existing canvas bar charts. */
(() => {
  const originalBarChart = window.barChart;
  if (typeof originalBarChart !== "function" || window.__vmestDepthBarsInstalled) return;
  window.__vmestDepthBarsInstalled = true;

  const colors = { positive: "#3288e8", negative: "#e45a65" };

  function shade(color, amount) {
    const match = /^#([\da-f]{6})$/i.exec(color || "");
    if (!match) return color;
    const channels = [0, 2, 4].map(index => parseInt(match[1].slice(index, index + 2), 16));
    const shaded = channels.map(channel => Math.round(amount >= 0
      ? channel + (255 - channel) * amount
      : channel * (1 + amount)));
    return `rgb(${shaded[0]}, ${shaded[1]}, ${shaded[2]})`;
  }

  function face(ctx, points, color, stroke) {
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let index = 1; index < points.length; index++) {
      ctx.lineTo(points[index][0], points[index][1]);
    }
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 0.8;
    ctx.stroke();
  }

  function drawExtrusion(canvas, labels, values, opts, progress) {
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (!width || !height || !values.length) return;

    // These paddings and scales match the dashboard's existing barChart renderer.
    const padding = { left: 48, right: 12, top: 12, bottom: 34 };
    let min = opts.min !== undefined ? opts.min : Math.min(0, ...values);
    let max = opts.max !== undefined ? opts.max : Math.max(...values);
    if (max === min) max = min + 1;
    const y = value => padding.top + (height - padding.top - padding.bottom)
      * (1 - (value - min) / (max - min));
    const step = (width - padding.left - padding.right) / values.length;
    const barWidth = Math.max(8, step * 0.48);
    const depthY = Math.max(3.5, Math.min(8, barWidth * 0.14)) * progress;
    const depthX = depthY * 1.15;

    ctx.save();
    // Keep all added faces inside the plot area; axis labels and ticks stay intact.
    ctx.beginPath();
    ctx.rect(padding.left, padding.top, width - padding.left - padding.right, height - padding.top - padding.bottom);
    ctx.clip();

    values.forEach((value, index) => {
      if (!Number.isFinite(value) || Math.abs(value) < 0.000001) return;
      const x = padding.left + step * index + (step - barWidth) / 2;
      const top = y(Math.max(value, 0));
      const bottom = y(Math.min(value, 0));
      const frontHeight = Math.max(1, bottom - top);
      const color = opts.colors?.[index] || (value < 0 ? colors.negative : colors.positive);
      const edge = "rgba(16, 39, 64, .34)";

      // Right and top faces extend from the unchanged front bar, making it read as a block.
      face(ctx,
        [[x + barWidth, top], [x + barWidth + depthX, top - depthY],
          [x + barWidth + depthX, top + frontHeight - depthY], [x + barWidth, top + frontHeight]],
        shade(color, -0.3), edge);
      face(ctx,
        [[x, top], [x + depthX, top - depthY], [x + barWidth + depthX, top - depthY], [x + barWidth, top]],
        shade(color, 0.25), "rgba(255, 255, 255, .72)");
    });
    ctx.restore();
    canvas.closest(".chart-wrap")?.classList.add("depth-bars-ready");
  }

  window.barChart = function drawDepthBarChart(id, labels, values, opts = {}) {
    const canvas = document.getElementById(id);
    if (!canvas || !Array.isArray(values) || values.length === 0) {
      return originalBarChart.call(this, id, labels, values, opts);
    }
    if (canvas.__vmestDepthFrame) cancelAnimationFrame(canvas.__vmestDepthFrame);

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const duration = 520;
    const start = performance.now();

    const paint = progress => {
      // Keep the existing renderer responsible for all data, scales, axes, labels and hover.
      originalBarChart.call(this, id, labels, values, opts);
      drawExtrusion(canvas, labels, values, opts, progress);
    };

    if (reducedMotion) {
      paint(1);
      canvas.__vmestDepthFrame = 0;
      return;
    }

    const animate = now => {
      const elapsed = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      paint(eased);
      if (elapsed < 1) canvas.__vmestDepthFrame = requestAnimationFrame(animate);
      else canvas.__vmestDepthFrame = 0;
    };
    canvas.__vmestDepthFrame = requestAnimationFrame(animate);
  };

  // Re-render the active screen once the wrapper is ready, so the first chart also gets depth.
  requestAnimationFrame(() => {
    if (typeof window.renderCurrentPage === "function") window.renderCurrentPage();
    else window.dispatchEvent(new Event("resize"));
  });
})();

