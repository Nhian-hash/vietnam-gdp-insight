import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { dataPath } from './data_paths.mjs';

const OUT = path.dirname(fileURLToPath(import.meta.url));
const RETRIEVED = new Date().toISOString().slice(0, 10);
async function writeDataset(name, content, encoding = 'utf8') {
  await writeFile(await dataPath(name, { forWrite: true }), content, encoding);
}
const wbIds = {
  gdpUsd: 'NY.GDP.MKTP.CD',
  agricultureUsd: 'NV.AGR.TOTL.CD',
  industryUsd: 'NV.IND.TOTL.CD',
  servicesUsd: 'NV.SRV.TOTL.CD',
  gdpReal2015: 'NY.GDP.MKTP.KD',
  realGrowth: 'NY.GDP.MKTP.KD.ZG',
};

function csvCell(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const s = String(value);
  return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}
function csv(rows) { return rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n'; }
function fmtNumber(value, digits = 6) {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  return Number(value.toFixed(digits)).toString();
}

async function fetchWdi(indicator, start = 1985, end = 2026) {
  const url = `https://api.worldbank.org/v2/country/VNM/indicator/${indicator}?date=${start}:${end}&format=json&per_page=1000`;
  const response = await fetch(url, { signal: AbortSignal.timeout(25000) });
  if (!response.ok) throw new Error(`World Bank ${indicator}: HTTP ${response.status}`);
  const body = await response.json();
  if (!Array.isArray(body) || !Array.isArray(body[1])) throw new Error(`World Bank returned an unexpected response for ${indicator}`);
  return new Map(body[1].filter(x => x.value !== null).map(x => [Number(x.date), Number(x.value)]));
}

function htmlAttrs(tag) {
  return Object.fromEntries([...tag.matchAll(/([\w:$-]+)="([^"]*)"/g)].map(m => [m[1].toLowerCase(), m[2]]));
}
function parseCsv(text) {
  const rows = [];
  let row = [], cell = '', quoted = false;
  text = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(cell); cell = ''; }
    else if (ch === '\n') { row.push(cell.replace(/\r$/, '')); rows.push(row); row = []; cell = ''; }
    else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell.replace(/\r$/, '')); rows.push(row); }
  return rows;
}

async function fetchPxWebCsv(tableUrl) {
  const pageResponse = await fetch(tableUrl, { signal: AbortSignal.timeout(25000), headers: { 'user-agent': 'Mozilla/5.0 (compatible; data-refresh/1.0)' } });
  if (!pageResponse.ok) throw new Error(`NSO PXWeb page: HTTP ${pageResponse.status}`);
  const html = await pageResponse.text();
  const formFields = new URLSearchParams();
  for (const match of html.matchAll(/<input\b[^>]*>/gis)) {
    const a = htmlAttrs(match[0]);
    if (a.name && a.type?.toLowerCase() === 'hidden') formFields.append(a.name, a.value ?? '');
  }
  const selects = [...html.matchAll(/<select\b[^>]*>[\s\S]*?<\/select>/gi)].map(match => {
    const open = match[0].match(/<select\b[^>]*>/i)?.[0] ?? '';
    return { tag: match[0], attrs: htmlAttrs(open) };
  });
  for (const select of selects) {
    const name = select.attrs.name;
    if (!name || name.includes('cboSelectLanguages') || name.includes('OutputFormatDropDownList')) continue;
    for (const opt of select.tag.matchAll(/<option\b[^>]*value="([^"]*)"/gi)) formFields.append(name, opt[1]);
  }
  const format = selects.find(s => s.attrs.name?.includes('OutputFormatDropDownList'));
  if (!format) throw new Error('NSO PXWeb CSV format control was not found');
  formFields.set(format.attrs.name, 'FileTypeCsvWithHeadingAndComma');
  formFields.set('ctl00$ContentPlaceHolderMain$VariableSelector1$VariableSelector1$ButtonViewTable', 'Continue');
  const cookie = (pageResponse.headers.get('set-cookie') ?? '').split(';')[0];
  const response = await fetch(tableUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded', cookie, 'user-agent': 'Mozilla/5.0 (compatible; data-refresh/1.0)' },
    body: formFields.toString(),
    redirect: 'follow',
    signal: AbortSignal.timeout(25000),
  });
  if (!response.ok) throw new Error(`NSO PXWeb CSV: HTTP ${response.status}`);
  const data = await response.text();
  if (!/"Year"/i.test(data.slice(0, 1000)) || data.length < 1000) throw new Error('NSO PXWeb did not return the expected table CSV');
  return data;
}

async function main() {
  const [gdpUsd, agricultureUsd, industryUsd, servicesUsd, gdpReal2015, realGrowth] = await Promise.all(
    Object.values(wbIds).map(id => fetchWdi(id))
  );
  const years = [...gdpUsd.keys()].sort((a, b) => a - b);
  if (!years.includes(2025)) throw new Error('World Bank has not returned the expected 2025 GDP observation');

  const annualRows = [['Nam_Goc', 'Year', 'Date', 'GDP_USD', 'GDP_USD_Billion']];
  const sectorRows = [['nam', 'tong_gdp_usd', 'gdp_nong_lam_thuy_san', 'gdp_cong_nghiep_xay_dung', 'gdp_dich_vu']];
  const realRows = [['nam', 'gdp_thuc_usd_2015', 'tang_truong_gdp_thuc_pct']];
  for (const year of years) {
    const gd = gdpUsd.get(year);
    annualRows.push([year, year, `${year}-01-01`, fmtNumber(gd, 2), fmtNumber(gd / 1e9, 6)]);
    sectorRows.push([
      year,
      fmtNumber(gd, 2),
      fmtNumber(agricultureUsd.get(year), 2),
      fmtNumber(industryUsd.get(year), 2),
      fmtNumber(servicesUsd.get(year), 2),
    ]);
    if (gdpReal2015.has(year) || realGrowth.has(year)) {
      realRows.push([year, fmtNumber(gdpReal2015.get(year), 2), fmtNumber(realGrowth.get(year), 6)]);
    }
  }
  await writeDataset('GDP_Vietnam_Annual.csv', csv(annualRows));
  await writeDataset('du_lieu_gdp_quoc_gia_co_cau_nganh.csv', csv(sectorRows));
  await writeDataset('du_lieu_gdp_thuc_va_tang_truong.csv', csv(realRows));

  // Latest official quarterly GDP release available from NSO at refresh time.
  // These are year-on-year growth estimates, not GDP level observations.
  const quarterlyGdpRows = [
    ['nam', 'quy', 'thoi_gian', 'tang_truong_gdp_so_voi_cung_ky_pct', 'nong_lam_thuy_san_yoy_pct', 'cong_nghiep_xay_dung_yoy_pct', 'dich_vu_yoy_pct', 'trang_thai'],
    [2026, 'Q1', '2026-Q1', 8.15, '', '', '', 'uoc_tinh_chinh_thuc'],
    [2026, 'Q2', '2026-Q2', 8.81, '', '', '', 'uoc_tinh_chinh_thuc'],
    [2026, 'Q3', '2026-Q3', 9.95, 4.21, 12.50, 9.54, 'uoc_tinh_chinh_thuc']
  ];
  await writeDataset('du_lieu_tang_truong_gdp_quy.csv', csv(quarterlyGdpRows));

  // Compatibility output for the current notebook/Power BI import. Annual values
  // are placed at December endpoints; the resulting monthly values are estimates,
  // not measured monthly GDP.
  // Treat each annual observation as the December endpoint of that reference year.
  // For Jan-Nov 1985, hold the first available annual value as a boundary value.
  const splineYears = years.map(y => y + 11 / 12);
  const splineValues = years.map(y => gdpUsd.get(y) / 1e9);
  const n = splineYears.length;
  const rhs = Array(n).fill(0), lower = Array(n).fill(0), diag = Array(n).fill(1), upper = Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    const h0 = splineYears[i] - splineYears[i - 1], h1 = splineYears[i + 1] - splineYears[i];
    lower[i] = h0; diag[i] = 2 * (h0 + h1); upper[i] = h1;
    rhs[i] = 6 * ((splineValues[i + 1] - splineValues[i]) / h1 - (splineValues[i] - splineValues[i - 1]) / h0);
  }
  for (let i = 1; i < n; i++) {
    const factor = lower[i] / diag[i - 1];
    diag[i] -= factor * upper[i - 1];
    rhs[i] -= factor * rhs[i - 1];
  }
  const second = Array(n).fill(0);
  second[n - 1] = rhs[n - 1] / diag[n - 1];
  for (let i = n - 2; i >= 0; i--) second[i] = (rhs[i] - upper[i] * second[i + 1]) / diag[i];
  const splineValue = x => {
    let i = Math.min(n - 2, Math.max(0, Math.floor(x - splineYears[0])));
    while (i < n - 2 && x > splineYears[i + 1]) i++;
    const h = splineYears[i + 1] - splineYears[i], a = (splineYears[i + 1] - x) / h, b = (x - splineYears[i]) / h;
    return a * splineValues[i] + b * splineValues[i + 1] + ((a ** 3 - a) * second[i] + (b ** 3 - b) * second[i + 1]) * h ** 2 / 6;
  };
  const monthRows = [['Date', 'Year', 'Month', 'GDP_USD_Billion']];
  let monthIndex = 0;
  for (let year = years[0]; year <= years.at(-1); year++) {
    for (let month = 1; month <= 12; month++) {
      const x = year + (month - 1) / 12;
      const estimated = x < splineYears[0] ? splineValues[0] : splineValue(x);
      monthRows.push([`${year}-${String(month).padStart(2, '0')}-01`, year, month, fmtNumber(estimated, 6)]);
      monthIndex++;
    }
  }
  await writeDataset('GDP_Vietnam_Monthly.csv', csv(monthRows));

  const pxUrl = 'https://pxweb.nso.gov.vn/pxweb/en/E%2011.%20CPI/E%2011.%20CPI__Px_E_11/E11.07.px/';
  const pxCsv = await fetchPxWebCsv(pxUrl);
  const pxRows = parseCsv(pxCsv);
  const header = pxRows.find(r => r[0] === 'Year' && r[1]?.toLowerCase().includes('commondity'));
  if (!header) throw new Error('Could not locate NSO CPI table header');
  const monthNames = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
  const monthCol = monthNames.map(name => header.findIndex(h => h.toLowerCase().replaceAll('.', '').startsWith(name)));
  if (monthCol.some(i => i < 0)) throw new Error('Could not map all months from NSO CPI table');
  const cpi = new Map();
  for (const row of pxRows) {
    const year = Number(row[0]);
    if (!Number.isInteger(year) || row[1]?.trim() !== 'Consumer price index') continue;
    for (let m = 1; m <= 12; m++) {
      const value = Number(row[monthCol[m - 1]]);
      if (Number.isFinite(value)) cpi.set(`${year}-${String(m).padStart(2, '0')}-01`, value);
    }
  }
  const dec2025 = cpi.get('2025-12-01');
  if (!dec2025) throw new Error('NSO base-2019 CPI table did not include Dec 2025');
  const cumulativePct2026 = [0.05, 1.19, 2.44, 3.31, 3.61, 3.21, 3.08, 3.57, 4.20];
  cumulativePct2026.forEach((pct, index) => {
    const month = index + 1;
    cpi.set(`2026-${String(month).padStart(2, '0')}-01`, dec2025 * (1 + pct / 100));
  });
  const cpiRows = [['thoi_gian', 'chi_so_cpi'], ...[...cpi.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([date, value]) => [date, fmtNumber(value, 6)])];
  await writeDataset('du_lieu_lam_phat_cpi.csv', csv(cpiRows));

  const status = [
    ['tep', 'dong_moc_du_lieu', 'ghi_chu'],
    ['GDP_Vietnam_Annual.csv', '1985-2025', 'GDP danh nghia USD hien hanh; so thuc 2025 moi nhat World Bank'],
    ['GDP_Vietnam_Monthly.csv', '1985-01..2025-12', 'Noi suy natural cubic spline giua cac moc GDP nam gan vao thang 12; khong phai GDP quan sat theo thang'],
    ['du_lieu_tang_truong_gdp_quy.csv', '2026-Q1..Q3', 'Tang truong GDP so voi cung ky theo uoc tinh chinh thuc NSO; khong phai quy mo GDP'],
    ['du_lieu_gdp_quoc_gia_co_cau_nganh.csv', '1985-2025', 'GDP va gia tri gia tang nganh theo World Bank; sector co the trong o trong khi nguon khong co quan sat'],
    ['du_lieu_gdp_thuc_va_tang_truong.csv', '1985-2025', 'GDP thuc USD co dinh nam 2015 va tang truong GDP thuc; dung lam muc tieu mo hinh uu tien'],
    ['du_lieu_lam_phat_cpi.csv', '2020-01..2026-09', '2020-2025 chi so CPI goc 2019 tu PXWeb; 2026-01..09 suy ra tu ty le CPI cong don NSO lam tron den 0.01%']
  ];
  await writeDataset('trang_thai_du_lieu.csv', csv(status));
  await writeFile(path.join(OUT, 'refresh_manifest.json'), JSON.stringify({
    retrieved_at_utc: new Date().toISOString(),
    data_cutoff: { annual_gdp: 2025, quarterly_gdp_growth: '2026-Q3', cpi: '2026-09' },
    sources: {
      world_bank_api: 'https://api.worldbank.org/v2/country/VNM/indicator/{indicator}?date=1985:2026&format=json&per_page=1000',
      nso_quarterly_gdp_2026: 'https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/',
      nso_pxweb_cpi: pxUrl,
      nso_cpi_2026_cumulative_changes: [
        'https://www.nso.gov.vn/en/data-and-statistics/2026/02/consumer-price-index-gold-price-index-and-us-dollar-price-index-for-january-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/03/consumer-price-index-gold-price-index-and-us-dollar-price-index-for-february-and-the-first-two-months-of-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/04/consumer-price-index-gold-us-dollar-price-index-in-march-and-the-first-quarter-in-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/05/consumer-price-index-gold-price-index-and-usd-price-index-for-april-and-the-first-four-months-of-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/07/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-june-2026-q2-2026-and-the-first-six-months-of-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/08/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-july-and-the-first-seven-months-of-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/09/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-august-and-eight-months-of-2026/',
        'https://www.nso.gov.vn/en/data-and-statistics/2026/10/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-september-2026-q3-2026-and-the-nine-months-of-2026/',
        'https://www.nso.gov.vn/en/cpi/'
      ]
    },
    indicators: wbIds,
    notes: {
      quarterly_gdp_2026: 'NSO quarterly year-on-year estimates for Q1-Q3 2026, from the official Q3 and first-nine-months release; not GDP level observations.',
      sectors: 'World Bank NV.AGR.TOTL.CD, NV.IND.TOTL.CD, NV.SRV.TOTL.CD; definitions are broad value-added groups.',
      monthly_gdp: 'Cubic spline is only a compatibility series for the current dashboard; do not use it as observed monthly GDP in backtests.',
      cpi_2026: '2026 monthly index values are reconstructed as Dec-2025 level times official cumulative CPI rate versus Dec-2025; rates are rounded in NSO press releases.'
    }
  }, null, 2), 'utf8');
  console.log(`Wrote ${years.length} annual rows (latest ${years.at(-1)}), ${monthIndex} monthly spline rows, and ${cpiRows.length - 1} CPI rows through 2026-09 to ${OUT}`);
}

await main();
