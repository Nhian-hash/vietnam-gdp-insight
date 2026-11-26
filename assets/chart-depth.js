/* Add an animated block extrusion to existing canvas bar charts. */
(() => {
  const originalBarChart = window.barChart;
  const originalLineChart = window.lineChart;
  const originalScatterChart = window.scatterChart;
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

  function pointSegments(values, x, y) {
    const segments = [];
    let active = [];
    values.forEach((value, index) => {
      if (value == null || !Number.isFinite(value)) {
        if (active.length) segments.push(active);
        active = [];
        return;
      }
      active.push({ x: x(index), y: y(value) });
    });
    if (active.length) segments.push(active);
    return segments;
  }

  function drawLineRelief(canvas, labels, series, opts, progress) {
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const padding = { left: 48, right: 12, top: 12, bottom: 30 };
    const validValues = series.flatMap(item => item.values.filter(value => value != null && Number.isFinite(value)));
    if (!width || !height || !validValues.length) return;

    let min = opts.min !== undefined ? opts.min : Math.min(...validValues);
    let max = opts.max !== undefined ? opts.max : Math.max(...validValues);
    if (max === min) max = min + 1;
    if (opts.zero) {
      min = Math.min(0, min);
      max = Math.max(0, max);
    }
    const span = max - min || 1;
    const x = index => padding.left + (width - padding.left - padding.right)
      * (labels.length === 1 ? 0.5 : index / (labels.length - 1));
    const y = value => padding.top + (height - padding.top - padding.bottom)
      * (1 - (value - min) / span);
    const ctx = canvas.getContext("2d");

    ctx.save();
    series.forEach(item => {
      const segments = pointSegments(item.values, x, y);
      const lineWidth = item.lineWidth || 2.4;
      const dash = item.dash || [];

      // A short lower shadow and a crisp top stroke give the line a raised, beveled edge.
      segments.forEach(segment => {
        if (segment.length < 2) return;
        ctx.beginPath();
        segment.forEach((point, index) => index
          ? ctx.lineTo(point.x, point.y + 1.5)
          : ctx.moveTo(point.x, point.y + 1.5));
        ctx.strokeStyle = shade(item.color, -0.34);
        ctx.lineWidth = lineWidth + 1.8;
        ctx.setLineDash(dash);
        ctx.globalAlpha = 0.22;
        ctx.stroke();

        ctx.beginPath();
        segment.forEach((point, index) => index
          ? ctx.lineTo(point.x, point.y)
          : ctx.moveTo(point.x, point.y));
        ctx.strokeStyle = item.color;
        ctx.lineWidth = lineWidth;
        ctx.globalAlpha = 0.96;
        ctx.stroke();
        ctx.setLineDash([]);
      });

      if (item.noPoints) return;
      const validCount = item.values.filter(value => value != null && Number.isFinite(value)).length;
      const markerStride = Math.max(1, Math.ceil(validCount / 42));
      item.values.forEach((value, index) => {
        if (value == null || !Number.isFinite(value) || (index % markerStride && index !== item.values.length - 1)) return;
        const px = x(index);
        const py = y(value);
        ctx.beginPath();
        ctx.arc(px + 0.7, py + 1.1, 3.1, 0, Math.PI * 2);
        ctx.fillStyle = shade(item.color, -0.3);
        ctx.globalAlpha = 0.28;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(px, py, 2.6, 0, Math.PI * 2);
        ctx.fillStyle = item.color;
        ctx.globalAlpha = 1;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(px - 0.8, py - 0.8, 0.72, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,.82)";
        ctx.fill();
      });

      // A single moving highlight animates along each data series without hiding its values.
      const segmentCount = segments.reduce((sum, segment) => sum + Math.max(0, segment.length - 1), 0);
      if (validCount > 1 && segmentCount > 0) {
        let target = progress * segmentCount;
        let tracer = null;
        for (const segment of segments) {
          for (let index = 1; index < segment.length; index++) {
            if (target <= 1) {
              const start = segment[index - 1];
              const end = segment[index];
              tracer = { x: start.x + (end.x - start.x) * target, y: start.y + (end.y - start.y) * target };
              break;
            }
            target -= 1;
          }
          if (tracer) break;
        }
        if (tracer) {
          ctx.beginPath();
          ctx.arc(tracer.x, tracer.y, 6, 0, Math.PI * 2);
          ctx.fillStyle = item.color;
          ctx.globalAlpha = 0.2;
          ctx.fill();
          ctx.beginPath();
          ctx.arc(tracer.x, tracer.y, 2.8, 0, Math.PI * 2);
          ctx.fillStyle = "#ffffff";
          ctx.globalAlpha = 1;
          ctx.fill();
          ctx.lineWidth = 1.8;
          ctx.strokeStyle = item.color;
          ctx.stroke();
        }
      }
    });
    ctx.restore();
    canvas.closest(".chart-wrap")?.classList.add("depth-lines-ready");
  }

  function drawScatterRelief(canvas, pair, progress) {
    const points = pair?.points || [];
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (!points.length || !width || !height) return;

    let minX = Math.min(...points.map(point => point.x));
    let maxX = Math.max(...points.map(point => point.x));
    let minY = Math.min(...points.map(point => point.y));
    let maxY = Math.max(...points.map(point => point.y));
    if (minX === maxX) { minX -= 1; maxX += 1; }
    if (minY === maxY) { minY -= 1; maxY += 1; }
    const dx = (maxX - minX) * 0.08;
    const dy = (maxY - minY) * 0.08;
    minX -= dx; maxX += dx; minY -= dy; maxY += dy;
    const padding = { left: 48, right: 14, top: 12, bottom: 30 };
    const x = value => padding.left + (width - padding.left - padding.right) * (value - minX) / (maxX - minX);
    const y = value => padding.top + (height - padding.top - padding.bottom) * (1 - (value - minY) / (maxY - minY));
    const ctx = canvas.getContext("2d");
    const activePoint = Math.min(points.length - 1, Math.floor(progress * points.length));

    ctx.save();
    points.forEach((point, index) => {
      const px = x(point.x);
      const py = y(point.y);
      // Keep every sample at its original center and radius; only add a shaded rim and highlight.
      ctx.beginPath();
      ctx.arc(px + 1.2, py + 1.8, 4.5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(15,39,64,.22)";
      ctx.fill();
      const gradient = ctx.createRadialGradient(px - 1.2, py - 1.3, 0.2, px, py, 4.4);
      gradient.addColorStop(0, "rgba(255,255,255,.96)");
      gradient.addColorStop(0.38, "#62b3ff");
      gradient.addColorStop(1, "#246fb7");
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      ctx.strokeStyle = "rgba(16,53,88,.45)";
      ctx.lineWidth = 0.7;
      ctx.stroke();

      if (index === activePoint) {
        ctx.beginPath();
        ctx.arc(px, py, 7.5, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(50,136,232,.48)";
        ctx.lineWidth = 1.4;
        ctx.stroke();
      }
    });
    ctx.restore();
    canvas.closest(".chart-wrap")?.classList.add("depth-scatter-ready");
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

  if (typeof originalLineChart === "function") {
    window.lineChart = function drawDepthLineChart(id, labels, series, opts = {}) {
      const canvas = document.getElementById(id);
      if (!canvas) return originalLineChart.call(this, id, labels, series, opts);
      if (canvas.__vmestDepthFrame) cancelAnimationFrame(canvas.__vmestDepthFrame);
      const duration = 680;
      const start = performance.now();
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      const paint = progress => {
        originalLineChart.call(this, id, labels, series, opts);
        drawLineRelief(canvas, labels, series, opts, progress);
      };
      if (reducedMotion) {
        paint(1);
        canvas.__vmestDepthFrame = 0;
        return;
      }
      const animate = now => {
        const progress = Math.min(1, (now - start) / duration);
        paint(1 - Math.pow(1 - progress, 3));
        if (progress < 1) canvas.__vmestDepthFrame = requestAnimationFrame(animate);
        else canvas.__vmestDepthFrame = 0;
      };
      canvas.__vmestDepthFrame = requestAnimationFrame(animate);
    };
  }

  if (typeof originalScatterChart === "function") {
    window.scatterChart = function drawDepthScatterChart(id, pair) {
      const canvas = document.getElementById(id);
      if (!canvas) return originalScatterChart.call(this, id, pair);
      if (canvas.__vmestDepthFrame) cancelAnimationFrame(canvas.__vmestDepthFrame);
      const duration = 560;
      const start = performance.now();
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      const paint = progress => {
        originalScatterChart.call(this, id, pair);
        drawScatterRelief(canvas, pair, progress);
      };
      if (reducedMotion) {
        paint(1);
        canvas.__vmestDepthFrame = 0;
        return;
      }
      const animate = now => {
        const progress = Math.min(1, (now - start) / duration);
        paint(1 - Math.pow(1 - progress, 3));
        if (progress < 1) canvas.__vmestDepthFrame = requestAnimationFrame(animate);
        else canvas.__vmestDepthFrame = 0;
      };
      canvas.__vmestDepthFrame = requestAnimationFrame(animate);
    };
  }

  // Re-render the active screen once the wrapper is ready, so the first chart also gets depth.
  requestAnimationFrame(() => {
    if (typeof window.renderCurrentPage === "function") window.renderCurrentPage();
    else window.dispatchEvent(new Event("resize"));
  });
})();

