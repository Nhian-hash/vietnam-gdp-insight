/* Draw bar charts as clean, beveled blocks without changing their data or axes. */
(() => {
  const drawFlatBars = window.barChart;
  if (typeof drawFlatBars !== "function" || window.__vmestDepthBarsInstalled) return;
  window.__vmestDepthBarsInstalled = true;

  function shade(color, amount) {
    if (typeof color !== "string") return color;
    let match = color.match(/^#([\da-f]{3}|[\da-f]{6})$/i);
    let rgb;
    if (match) {
      let hex = match[1];
      if (hex.length === 3) hex = hex.split("").map(ch => ch + ch).join("");
      rgb = [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16));
    } else {
      match = color.match(/^rgba?\(\s*(\d+)\D+(\d+)\D+(\d+)/i);
      if (!match) return color;
      rgb = [Number(match[1]), Number(match[2]), Number(match[3])];
    }
    const next = rgb.map(channel => Math.round(amount >= 0
      ? channel + (255 - channel) * amount
      : channel * (1 + amount)));
    return `rgb(${next[0]}, ${next[1]}, ${next[2]})`;
  }

  function polygon(ctx, points, fill, outline) {
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i][0], points[i][1]);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (outline) {
      ctx.strokeStyle = outline;
      ctx.lineWidth = 0.7;
      ctx.stroke();
    }
  }

  window.barChart = function drawDepthBarChart(id, labels, values, opts = {}) {
    const canvas = document.getElementById(id);
    if (!canvas || !values?.length) return drawFlatBars(id, labels, values, opts);
    if (canvas.__vmestDepthFrame) cancelAnimationFrame(canvas.__vmestDepthFrame);

    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const duration = 620;
    const startedAt = performance.now();
    const min = opts.min !== undefined ? opts.min : Math.min(0, ...values);
    let max = opts.max !== undefined ? opts.max : Math.max(...values);
    if (max === min) max = min + 1;
    const height = canvas.getBoundingClientRect().height;
    const plotTop = 12;
    const plotHeight = Math.max(1, height - 12 - 34);
    const valueY = value => plotTop + plotHeight * (1 - (value - min) / (max - min));
    const zeroY = valueY(0);

    const draw = progress => {
      const ctx = canvas.getContext("2d");
      const fillRect = ctx.fillRect;
      const fillText = ctx.fillText;
      let barIndex = -1;
      let barTextIndex = 0;
      const depthScale = Math.max(0.2, Math.min(1, progress));
      ctx.fillRect = function drawBlock(x, y, width, fullHeight) {
        barIndex++;
        barTextIndex = 0;
        if (!Number.isFinite(values[barIndex]) || width < 4 || fullHeight < 1.5) {
          return fillRect.call(this, x, y, width, fullHeight);
        }

        const baseColor = this.fillStyle;
        const rise = Math.max(3, Math.min(9, width * 0.16)) * depthScale;
        const dx = rise * 1.12;
        let frontY = y;
        let frontHeight = fullHeight;
        if (progress < 1) {
          if (y < zeroY) {
            frontY = zeroY - (zeroY - y) * progress;
            frontHeight = Math.max(0.8, fullHeight * progress);
          } else {
            frontY = zeroY;
            frontHeight = Math.max(0.8, fullHeight * progress);
          }
        }

        this.save();
        polygon(this,
          [[x + width, frontY], [x + width + dx, frontY - rise],
            [x + width + dx, frontY + frontHeight - rise], [x + width, frontY + frontHeight]],
          shade(baseColor, -0.30), "rgba(15, 35, 58, .18)");
        polygon(this,
          [[x, frontY], [x + dx, frontY - rise], [x + width + dx, frontY - rise], [x + width, frontY]],
          shade(baseColor, 0.34), "rgba(255, 255, 255, .62)");

        this.fillStyle = baseColor;
        this.shadowColor = "rgba(17, 39, 62, .16)";
        this.shadowBlur = 6;
        this.shadowOffsetX = 2;
        this.shadowOffsetY = 2;
        fillRect.call(this, x, frontY, width, frontHeight);
        this.shadowColor = "transparent";
        this.shadowBlur = 0;
        this.shadowOffsetX = 0;
        this.shadowOffsetY = 0;
        this.strokeStyle = "rgba(255, 255, 255, .48)";
        this.lineWidth = 0.7;
        this.strokeRect(x + 0.35, frontY + 0.35, Math.max(0, width - 0.7), Math.max(0, frontHeight - 0.7));
        this.restore();
      };

      ctx.fillText = function liftDataLabels(text, x, y, ...rest) {
        if (barIndex >= 0) {
          barTextIndex++;
          if (opts.labels && barTextIndex === 2) {
            if (progress < 0.82) return;
            const rise = Math.max(3, Math.min(9, canvas.getBoundingClientRect().width / Math.max(1, values.length) * 0.48 * 0.16));
            y += values[barIndex] < 0 ? rise + 3 : -rise - 3;
          }
        }
        return fillText.call(this, text, x, y, ...rest);
      };

      try {
        drawFlatBars.call(this, id, labels, values, opts);
      } finally {
        ctx.fillRect = fillRect;
        ctx.fillText = fillText;
      }
      canvas.closest(".chart-wrap")?.classList.add("depth-bars-ready");
    };

    if (reducedMotion) {
      draw(1);
      canvas.__vmestDepthFrame = 0;
      return;
    }

    const animate = now => {
      const t = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      draw(eased);
      if (t < 1) canvas.__vmestDepthFrame = requestAnimationFrame(animate);
      else canvas.__vmestDepthFrame = 0;
    };
    canvas.__vmestDepthFrame = requestAnimationFrame(animate);
  };

  window.dispatchEvent(new Event("resize"));
})();

