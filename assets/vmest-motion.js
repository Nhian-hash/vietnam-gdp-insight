/* Organize the existing page links on older generated HTML. No routes or data change. */
(() => {
  const nav = document.querySelector("nav.nav");
  if (!nav || nav.querySelector(".nav-group")) return;

  const groups = [
    { label: "Tổng quan", aria: "Tổng quan", pages: ["overview"] },
    {
      label: "Phân tích kinh tế",
      aria: "Phân tích kinh tế",
      pages: ["macro", "macro-compare", "growth-drivers"],
    },
    {
      label: "Ngành & khu vực",
      aria: "Ngành và khu vực",
      pages: [
        "sector-agriculture",
        "sector-industry",
        "sector-services",
        "trade",
        "retail-fdi",
        "regional",
      ],
    },
    {
      label: "Mô hình & hệ thống",
      aria: "Mô hình và hệ thống",
      pages: ["models", "data-status", "project-info"],
    },
  ];

  const links = [...nav.querySelectorAll(":scope > .nav-link")];
  for (const group of groups) {
    const members = links.filter((link) => group.pages.includes(link.dataset.page));
    if (!members.length) continue;

    const wrapper = document.createElement("div");
    wrapper.className = "nav-group";
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", group.aria);

    const label = document.createElement("span");
    label.className = "nav-group-label";
    label.textContent = group.label;
    wrapper.append(label, ...members);
    nav.append(wrapper);
  }

  const remaining = links.filter((link) => link.parentElement === nav);
  if (remaining.length) {
    const wrapper = document.createElement("div");
    wrapper.className = "nav-group";
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", "Mục khác");
    const label = document.createElement("span");
    label.className = "nav-group-label";
    label.textContent = "Mục khác";
    wrapper.append(label, ...remaining);
    nav.append(wrapper);
  }
})();

