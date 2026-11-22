/* V-MEST historical cutoff backtest UI. Model fitting is deliberately offline. */
(() => {
  const $ = (id) => document.getElementById(id);
  const modelStyle = {
    Naive: { label: "Naive", color: "#697586" },
    Drift: { label: "Drift", color: "#20936d" },
    SARIMAX: { label: "SARIMAX (1,1,0)", color: "#e28b24" },
    GRU: { label: "GRU", color: "#7757c8" },
    LSTM: { label: "LSTM", color: "#d94f61" },
  };
  let currentResponse = null;
  let requestNumber = 0;
  let activeController = null;
  let autoLoadEligible = false;
  let retryTimer = null;
  let retryDelayMs = 5000;

  const format = (value, digits = 2) => Number(value).toLocaleString("vi-VN", {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  });
  const fmtBillion = (value) => value == null ? "—" : `${format(value / 1e9, 2)} tỷ USD`;

  function setStatus(message, isError = false) {
    const node = $("arena-status");
    node.replaceChildren(document.createTextNode(message));
    node.classList.toggle("error", isError);
    if (isError) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "select export-btn";
      retry.textContent = "Thử lại";
      retry.addEventListener("click", () => {
        autoLoadEligible = true;
        loadScenario();
      });
      node.append(document.createTextNode(" "), retry);
    }
  }

  function checkedModels() {
    return Object.keys(modelStyle).filter((key) => $(`arena-model-${key}`).checked);
  }

  function drawChart() {
    const canvas = $("arena-chart");
    const wrapper = canvas?.parentElement;
    if (!canvas || !wrapper || !currentResponse) return;
    const scenario = currentResponse.scenario;
    const visibleModels = checkedModels();
    const years = [
      ...scenario.history.map((row) => row.year),
      ...scenario.actuals.map((row) => row.year),
    ];
    const uniqueYears = [...new Set(years)].sort((a, b) => a - b);
    const yearIndex = new Map(uniqueYears.map((year, index) => [year, index]));
    const actualByYear = new Map(scenario.history.map((row) => [row.year, row.value_usd_2015]));
    for (const row of scenario.actuals) actualByYear.set(row.year, row.actual_usd_2015);
    const series = [{
      key: "actual", label: "GDP thực tế", color: "#3288e8",
      values: uniqueYears.map((year) => actualByYear.get(year) == null ? null : actualByYear.get(year) / 1e9),
    }];
    for (const model of visibleModels) {
      const path = scenario.forecasts[model];
      if (!path) continue;
      const values = Array(uniqueYears.length).fill(null);
      const anchorIndex = yearIndex.get(scenario.cutoff_year);
      const lastObserved = scenario.history.at(-1)?.value_usd_2015;
      if (anchorIndex != null && lastObserved != null) values[anchorIndex] = lastObserved / 1e9;
      for (const point of path.points) values[yearIndex.get(point.year)] = point.predicted_usd_2015 / 1e9;
      series.push({ key: model, label: modelStyle[model].label, color: modelStyle[model].color, values });
    }

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const width = rect.width;
    const height = rect.height;
    const pad = { left: 65, right: 14, top: 22, bottom: 34 };
    const plotWidth = Math.max(10, width - pad.left - pad.right);
    const plotHeight = Math.max(10, height - pad.top - pad.bottom);
    const chartValues = series.flatMap((item) => item.values.filter(Number.isFinite));
    const sarimax = scenario.forecasts.SARIMAX?.points || [];
    for (const point of sarimax) {
      if (point.lower95_usd_2015 != null) chartValues.push(point.lower95_usd_2015 / 1e9);
      if (point.upper95_usd_2015 != null) chartValues.push(point.upper95_usd_2015 / 1e9);
    }
    if (!chartValues.length) return;
    const min = 0;
    const max = Math.max(...chartValues) * 1.08 || 1;
    const x = (index) => pad.left + plotWidth * (uniqueYears.length <= 1 ? 0.5 : index / (uniqueYears.length - 1));
    const y = (value) => pad.top + plotHeight * (1 - (value - min) / (max - min));
    const muted = getComputedStyle(document.body).getPropertyValue("--muted").trim() || "#718096";
    const grid = getComputedStyle(document.body).getPropertyValue("--line").trim() || "#e1e7ef";
    ctx.clearRect(0, 0, width, height);
    ctx.font = "10px Segoe UI, Arial";
    ctx.textBaseline = "middle";
    ctx.fillStyle = muted; ctx.textAlign = "left";
    ctx.fillText("Tỷ USD · giá cố định 2015", pad.left, 9);
    for (let tick = 0; tick <= 4; tick += 1) {
      const value = max * tick / 4;
      const yy = y(value);
      ctx.strokeStyle = grid;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.left, yy); ctx.lineTo(width - pad.right, yy); ctx.stroke();
      ctx.fillStyle = muted;
      ctx.textAlign = "right";
      ctx.fillText(format(value, 0), pad.left - 8, yy);
    }
    const labelStep = Math.max(1, Math.ceil(uniqueYears.length / 7));
    uniqueYears.forEach((year, index) => {
      if (index % labelStep === 0 || index === uniqueYears.length - 1) {
        ctx.fillStyle = muted; ctx.textAlign = "center";
        ctx.fillText(String(year), x(index), height - 13);
      }
    });

    // Shaded SARIMAX interval is drawn only when that model is visible.
    if (visibleModels.includes("SARIMAX")) {
      const points = sarimax.filter((point) => point.lower95_usd_2015 != null && point.upper95_usd_2015 != null);
      if (points.length) {
        ctx.beginPath();
        points.forEach((point, index) => {
          const xi = x(yearIndex.get(point.year));
          index ? ctx.lineTo(xi, y(point.lower95_usd_2015 / 1e9)) : ctx.moveTo(xi, y(point.lower95_usd_2015 / 1e9));
        });
        points.slice().reverse().forEach((point) => ctx.lineTo(x(yearIndex.get(point.year)), y(point.upper95_usd_2015 / 1e9)));
        ctx.closePath(); ctx.globalAlpha = 0.14; ctx.fillStyle = modelStyle.SARIMAX.color; ctx.fill(); ctx.globalAlpha = 1;
      }
    }

    // The cutoff marker separates training history from holdout/forecast years.
    const cutoffIndex = yearIndex.get(scenario.cutoff_year);
    if (cutoffIndex != null) {
      ctx.save(); ctx.strokeStyle = "#b83b48"; ctx.setLineDash([5, 4]); ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(x(cutoffIndex), pad.top); ctx.lineTo(x(cutoffIndex), height - pad.bottom); ctx.stroke(); ctx.restore();
      ctx.fillStyle = "#b83b48"; ctx.textAlign = "center"; ctx.textBaseline = "top";
      ctx.fillText(`Mốc cắt ${scenario.cutoff_year}`, x(cutoffIndex), 3);
    }

    for (const item of series) {
      ctx.beginPath();
      let drawing = false;
      item.values.forEach((value, index) => {
        if (value == null || !Number.isFinite(value)) { drawing = false; return; }
        drawing ? ctx.lineTo(x(index), y(value)) : ctx.moveTo(x(index), y(value));
        drawing = true;
      });
      ctx.strokeStyle = item.color; ctx.lineWidth = item.key === "actual" ? 2.8 : 2.1;
      if (item.key !== "actual") ctx.setLineDash([5, 3]);
      ctx.stroke(); ctx.setLineDash([]);
      item.values.forEach((value, index) => {
        if (value == null || !Number.isFinite(value)) return;
        ctx.beginPath(); ctx.arc(x(index), y(value), item.key === "actual" ? 2.5 : 2, 0, Math.PI * 2);
        ctx.fillStyle = item.color; ctx.fill();
      });
    }
    const tooltip = $("arena-tooltip");
    canvas.onpointermove = (event) => {
      const bounds = canvas.getBoundingClientRect();
      const localX = event.clientX - bounds.left;
      const nearest = Math.max(0, Math.min(uniqueYears.length - 1, Math.round((localX - pad.left) / plotWidth * (uniqueYears.length - 1))));
      const year = uniqueYears[nearest];
      const lines = [`Năm ${year}`];
      for (const item of series) {
        const value = item.values[nearest];
        if (value != null && Number.isFinite(value)) lines.push(`${item.label}: ${format(value, 2)} tỷ USD`);
      }
      const actual = actualByYear.get(year);
      const rows = scenario.forecasts.SARIMAX?.points || [];
      const interval = rows.find((point) => point.year === year);
      if (interval && interval.lower95_usd_2015 != null) {
        lines.push(`SARIMAX 95%: ${format(interval.lower95_usd_2015 / 1e9, 2)}–${format(interval.upper95_usd_2015 / 1e9, 2)} tỷ USD`);
      }
      tooltip.textContent = lines.join("\n"); tooltip.style.whiteSpace = "pre-line";
      tooltip.style.display = "block";
      tooltip.style.left = `${Math.min(width - 270, Math.max(4, localX + 10))}px`;
      tooltip.style.top = `${Math.max(4, event.clientY - bounds.top - 50)}px`;
    };
    canvas.onpointerleave = () => { tooltip.style.display = "none"; };
  }

  function renderLegend() {
    const legend = $("arena-legend");
    legend.replaceChildren();
    const entries = [{ label: "GDP thực tế", color: "#3288e8", dashed: false },
      ...Object.values(modelStyle).filter((model) => checkedModels().some((key) => modelStyle[key] === model))
        .map((model) => ({ label: model.label, color: model.color, dashed: true }))];
    for (const item of entries) {
      const span = document.createElement("span");
      const swatch = document.createElement("i"); swatch.className = "arena-swatch";
      swatch.style.background = item.color;
      if (item.dashed) swatch.style.background = `repeating-linear-gradient(90deg,${item.color} 0 5px,transparent 5px 8px)`;
      span.append(swatch, document.createTextNode(item.label)); legend.appendChild(span);
    }
    if (checkedModels().includes("SARIMAX")) {
      const span = document.createElement("span");
      const swatch = document.createElement("i"); swatch.className = "arena-swatch";
      swatch.style.height = "8px"; swatch.style.background = "rgba(226,139,36,.2)";
      span.append(swatch, document.createTextNode("Khoảng dự báo SARIMAX 95%")); legend.appendChild(span);
    }
  }

  function renderScoreboard() {
    const body = $("arena-scoreboard");
    body.replaceChildren();
    if (!currentResponse) return;
    const rankBy = $("arena-rank-by").value;
    const metricKey = rankBy === "mae" ? "mae_usd_2015" : "rmse_usd_2015";
    const rows = currentResponse.scenario.metrics.slice().sort((a, b) => {
      const av = a[metricKey]; const bv = b[metricKey];
      return (av == null) - (bv == null) || (av ?? Infinity) - (bv ?? Infinity);
    });
    for (const [index, row] of rows.entries()) {
      const tr = document.createElement("tr");
      const values = [
        index + 1,
        modelStyle[row.model]?.label || row.model,
        row.n,
        fmtBillion(row.mae_usd_2015),
        fmtBillion(row.rmse_usd_2015),
        row.mape_pct == null ? "—" : `${format(row.mape_pct, 2)}%`,
        row.coverage_95_pct == null ? "—" : `${format(row.coverage_95_pct, 1)}% (${row.covered_n}/${row.coverage_n})`,
      ];
      values.forEach((value, cellIndex) => {
        const cell = document.createElement(cellIndex === 0 ? "th" : "td");
        cell.textContent = String(value);
        if (cellIndex === 0) cell.scope = "row";
        tr.appendChild(cell);
      });
      if (index === 0 && row[metricKey] != null) tr.classList.add("arena-best");
      body.appendChild(tr);
    }
  }

  function renderResponse() {
    const data = currentResponse;
    if (!data) return;
    const scenario = data.scenario;
    const from = scenario.history[0]?.year ?? "—";
    const actualYears = scenario.actuals.filter((row) => row.actual_usd_2015 != null).map((row) => row.year);
    const actualRange = actualYears.length ? `${actualYears[0]}–${actualYears.at(-1)}` : "chưa có";
    $("arena-scenario-title").textContent = `${scenario.event_label} · mốc ${scenario.cutoff_year}`;
    $("arena-scenario-badge").textContent = scenario.status === "forecast_only" ? "Dự báo chưa có thực tế đối chiếu" : "Kiểm định ngoài mẫu";
    $("arena-period-meta").textContent = `Huấn luyện ${from}–${scenario.cutoff_year} · kiểm tra thực tế ${actualRange} · chân trời ${scenario.horizon} năm`;
    $("arena-method-meta").textContent = `${data.target.source} · ${data.target.indicator} · GDP thực ${data.target.unit} · cập nhật artifact ${data.generated_at_utc}`;
    const note = scenario.notes?.join(" ") || "";
    const coverage = scenario.sarimax_coverage_note || "";
    const limitations = data.methodology.limitations?.join(" ") || "";
    $("arena-caveat").textContent = `${note} ${coverage} ${limitations}`;
    renderLegend(); renderScoreboard(); drawChart();
  }

  function scheduleRetry() {
    if (!autoLoadEligible || retryTimer) return;
    retryTimer = setTimeout(() => {
      retryTimer = null;
      if (autoLoadEligible && !currentResponse) loadScenario();
    }, retryDelayMs);
    retryDelayMs = Math.min(retryDelayMs * 2, 30000);
  }

  async function loadScenario() {
    clearTimeout(retryTimer);
    retryTimer = null;
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const currentRequest = ++requestNumber;
    const cutoff = $("arena-cutoff").value;
    const horizon = $("arena-horizon").value;
    setStatus("Đang tải kết quả đã tiền tính…");
    const slowTimer = setTimeout(() => {
      if (currentRequest === requestNumber) setStatus("Máy chủ đang khởi động, vui lòng chờ…");
    }, 5000);
    const timeoutTimer = setTimeout(() => controller.abort(), 60000);
    try {
      const url = `/api/v1/backtest-arena?cutoff_year=${encodeURIComponent(cutoff)}&horizon=${encodeURIComponent(horizon)}`;
      const response = await fetch(url, { cache: "no-store", signal: controller.signal });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      if (currentRequest !== requestNumber) return;
      currentResponse = payload;
      retryDelayMs = 5000;
      setStatus("Đã tải kết quả kiểm định.");
      renderResponse();
    } catch (error) {
      if (currentRequest !== requestNumber) return;
      currentResponse = null;
      const message = controller.signal.aborted
        ? "Máy chủ đang khởi động, vui lòng chờ…"
        : `Không tải được artifact: ${error.message}`;
      setStatus(message, true);
      $("arena-scoreboard").replaceChildren();
      const canvas = $("arena-chart");
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      scheduleRetry();
    } finally {
      clearTimeout(slowTimer);
      clearTimeout(timeoutTimer);
      if (activeController === controller) activeController = null;
    }
  }

  // Keep the detailed cutoff evaluation collapsed until requested. Rendering
  // after expansion ensures the chart measures its visible container correctly.
  const arena = $("model-arena");
  arena.addEventListener("toggle", () => {
    if (!arena.open) return;
    autoLoadEligible = true;
    if (!currentResponse) loadScenario();
    else { renderLegend(); renderScoreboard(); drawChart(); }
  });
  if ("IntersectionObserver" in window) {
    const arenaObserver = new IntersectionObserver((entries) => {
      const entry = entries[0];
      autoLoadEligible = Boolean(entry?.isIntersecting);
      if (autoLoadEligible && !currentResponse && !activeController) loadScenario();
    }, { rootMargin: "120px 0px" });
    arenaObserver.observe(arena);
  }
  $("arena-cutoff").addEventListener("change", () => loadScenario());
  $("arena-horizon").addEventListener("change", () => loadScenario());
  $("arena-rank-by").addEventListener("change", renderScoreboard);
  Object.keys(modelStyle).forEach((key) => $(`arena-model-${key}`).addEventListener("change", () => {
    if (currentResponse) { renderLegend(); drawChart(); }
  }));
  $("theme").addEventListener("click", () => window.setTimeout(drawChart, 0));
  window.addEventListener("resize", drawChart);
})();

