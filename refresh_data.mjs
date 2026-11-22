import { readFile, writeFile } from 'node:fs/promises';
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
  let lastError;
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(90000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json();
      if (!Array.isArray(body) || !Array.isArray(body[1])) throw new Error('unexpected API response');
      return new Map(body[1].filter(x => x.value !== null).map(x => [Number(x.date), Number(x.value)]));
    } catch (error) {
      lastError = error;
      if (attempt < 4) await new Promise(resolve => setTimeout(resolve, 1500 * attempt));
    }
  }
  throw new Error(`World Bank ${indicator} failed after 4 attempts: ${lastError?.message ?? 'unknown error'}`);
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
  const pageResponse = await fetch(tableUrl, { signal: AbortSignal.timeout(60000), headers: { 'user-agent': 'Mozilla/5.0 (compatible; data-refresh/1.0)' } });
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
    signal: AbortSignal.timeout(60000),
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
  if (years.length < 35 || years.at(-1) < 2025) throw new Error('World Bank GDP series is incomplete or older than 2025');

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

  // Quarterly GDP is intentionally left untouched here. The World Bank annual
  // refresh must never overwrite the separate NSO quarterly release series.

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
  if (cpi.size < 60) throw new Error('NSO CPI source returned too few observed months');
  const latestCpiPeriod = [...cpi.keys()].sort().at(-1);
  const earliestCpiPeriod = [...cpi.keys()].sort()[0];
  const cpiRows = [['thoi_gian', 'chi_so_cpi'], ...[...cpi.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([date, value]) => [date, fmtNumber(value, 6)])];

  await writeDataset('du_lieu_lam_phat_cpi.csv', csv(cpiRows));

  // Current monthly CPI rates are published through NSO release pages; E11.07
  // currently ends earlier, so keep published rates in a separate, unlinked series.
  const cpiReleaseArchiveUrl = 'https://www.nso.gov.vn/en/cpi/';
  const archiveResponse = await fetch(cpiReleaseArchiveUrl, {
    headers: { 'user-agent': 'Mozilla/5.0 (compatible; V-MEST-data-refresh/1.0)' },
    signal: AbortSignal.timeout(60000),
  });
  if (!archiveResponse.ok) throw new Error(`NSO CPI release archive: HTTP ${archiveResponse.status}`);
  const archiveHtml = await archiveResponse.text();
  const decodeHtml = value => value
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/\s+/g, ' ')
    .trim();
  const releaseLinks = [...archiveHtml.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)]
    .map(match => ({ url: new URL(match[1], cpiReleaseArchiveUrl).toString(), text: decodeHtml(match[2]) }))
    .filter(item => item.url.includes('/data-and-statistics/') && /consumer-price-index/i.test(item.url))
    .map(item => {
      const periodMatch = item.text.match(/Reference period:\s*(\d{1,2})\/(20\d{2})/i);
      const issueMatch = item.text.match(/Date of issue:\s*(\d{1,2})\/(\d{1,2})\/(20\d{2})/i);
      if (!periodMatch) return null;
      const period = `${periodMatch[2]}-${periodMatch[1].padStart(2, '0')}-01`;
      const issueDate = issueMatch ? `${issueMatch[3]}-${issueMatch[2].padStart(2, '0')}-${issueMatch[1].padStart(2, '0')}` : '';
      return { ...item, period, issueDate };
    })
    .filter(Boolean);
  const uniqueReleaseLinks = [...new Map(releaseLinks.map(item => [item.period, item])).values()]
    .sort((a, b) => b.period.localeCompare(a.period))
    .slice(0, 12);
  if (!uniqueReleaseLinks.length) throw new Error('NSO CPI archive has no monthly CPI releases with reference periods');
  const reportedReleases = [];
  for (const item of uniqueReleaseLinks) {
    const reportResponse = await fetch(item.url, {
      headers: { 'user-agent': 'Mozilla/5.0 (compatible; V-MEST-data-refresh/1.0)' },
      signal: AbortSignal.timeout(60000),
    });
    if (!reportResponse.ok) throw new Error(`NSO CPI release ${item.period}: HTTP ${reportResponse.status}`);
    const reportHtml = await reportResponse.text();
    const paragraphs = [...reportHtml.matchAll(/<p\b[^>]*>([\s\S]*?)<\/p>/gi)]
      .map(match => decodeHtml(match[1]))
      .filter(Boolean);
    const summary = paragraphs.find(text => /consumer price index/i.test(text) && /%/.test(text));
    if (!summary) throw new Error(`NSO CPI release ${item.period}: summary paragraph missing`);
    const monthlySentence = summary.split(/(?<=[.!?])\s+/).find(text => /previous month|month-on-month/i.test(text)) ?? summary;
    const monthlyMatch = monthlySentence.match(/(\d+(?:[.,]\d+)?)\s*%/);
    const annualMatch =
      summary.match(/(\d+(?:[.,]\d+)?)\s*%\s*(?:year[- ]on[- ]year|year on year)/i) ??
      summary.match(/(\d+(?:[.,]\d+)?)\s*%\s+(?:over|compared (?:with|to))\s+(?:the\s+)?same period (?:last year|of the previous year)/i);
    const decemberMatch = summary.match(/(\d+(?:[.,]\d+)?)\s*%\s+compared (?:with|to) December/i);
    const averageSentence = paragraphs
      .flatMap(text => text.split(/(?<=[.!?])\s+/))
      .find(text => /on average/i.test(text) && /(?:consumer price index|\bCPI\b)/i.test(text) && /\bmonths?\b/i.test(text)) ?? '';
    const averageMatch = averageSentence.match(/(?:consumer price index|\bCPI\b)[^.]*?(\d+(?:[.,]\d+)?)\s*%/i);
    const coreMatch = averageSentence.match(/core inflation[^.]*?(\d+(?:[.,]\d+)?)\s*%/i);
    if (!monthlyMatch || !annualMatch) throw new Error(`NSO CPI release ${item.period}: cannot parse official month-on-month or year-on-year rate`);
    const toNumber = match => match ? Number(match[1].replace(',', '.')) : '';
    const formatReported = value => value === '' ? '' : fmtNumber(value, 6);
    const monthlyText = monthlySentence.toLowerCase();
    const monthlySign = /decreas|fell|declin|drop|down/.test(monthlyText) ? -1 : 1;
    reportedReleases.push([
      item.period,
      item.period.slice(0, 4),
      item.period.slice(5, 7),
      formatReported(monthlySign * toNumber(monthlyMatch)),
      formatReported(toNumber(decemberMatch)),
      formatReported(toNumber(annualMatch)),
      formatReported(toNumber(averageMatch)),
      formatReported(toNumber(coreMatch)),
      'cong_bo_chinh_thuc_nso',
      item.issueDate,
      item.url,
      'Các tốc độ do NSO công bố; không phải mức chỉ số CPI và không nối chuỗi qua đổi gốc.',
    ]);
  }
  const releaseName = 'du_lieu_cpi_cong_bo_thang.csv';
  let priorReleases = [];
  try {
    priorReleases = parseCsv(await readFile(await dataPath(releaseName), 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const releaseHeader = [
    'thoi_gian', 'nam', 'thang', 'cpi_thay_doi_so_voi_thang_truoc_pct',
    'cpi_thay_doi_so_voi_thang_12_pct', 'cpi_thay_doi_cung_ky_pct',
    'cpi_binh_quan_luy_ke_yoy_pct', 'lam_phat_co_ban_binh_quan_luy_ke_pct',
    'trang_thai', 'ngay_cong_bo', 'nguon', 'ghi_chu',
  ];
  const releaseByPeriod = new Map();
  for (const row of priorReleases.slice(1)) if (row[0]) releaseByPeriod.set(row[0], row);
  for (const row of reportedReleases) releaseByPeriod.set(row[0], row);
  const allReleases = [...releaseByPeriod.values()].sort((a, b) => a[0].localeCompare(b[0]));
  await writeDataset(releaseName, csv([releaseHeader, ...allReleases]));
  const latestReportedCpi = allReleases.at(-1);
  const latestCpiReleaseUrl = latestReportedCpi?.[10] ?? '';


  const status = [
    ['tep', 'dong_moc_du_lieu', 'ghi_chu'],
    ['GDP_Vietnam_Annual.csv', `${years[0]}-${years.at(-1)}`, 'GDP danh nghia USD hien hanh; quan sat World Bank WDI'],
    ['GDP_Vietnam_Monthly.csv', `${years[0]}-01..${years.at(-1)}-12`, 'Noi suy natural cubic spline giua cac moc GDP nam; khong phai GDP quan sat theo thang'],
    ['du_lieu_tang_truong_gdp_quy.csv', '2026-Q1..Q3', 'Tang truong GDP so voi cung ky theo uoc tinh chinh thuc NSO; khong phai quy mo GDP'],
    ['du_lieu_gdp_quoc_gia_co_cau_nganh.csv', `${years[0]}-${years.at(-1)}`, 'GDP va gia tri gia tang nganh theo World Bank WDI; gia tri nganh de trong neu nguon khong co quan sat'],
    ['du_lieu_gdp_thuc_va_tang_truong.csv', `${years[0]}-${Math.max(...gdpReal2015.keys())}`, 'GDP thuc USD co dinh nam 2015 va tang truong GDP thuc theo World Bank WDI'],
    ['du_lieu_lam_phat_cpi.csv', `${earliestCpiPeriod}..${latestCpiPeriod}`, 'Chi so CPI quan sat theo NSO PXWeb; khong noi suy tu ty le cong don'],
    ['du_lieu_cpi_cong_bo_thang.csv', `${allReleases[0]?.[0] ?? ''}..${latestReportedCpi?.[0] ?? ''}`, 'Ty le CPI do thong cao NSO cong bo; luu rieng voi muc chi so PXWeb']
  ];
  await writeDataset('trang_thai_du_lieu.csv', csv(status));
  const quarterSource = parseCsv(await readFile(await dataPath('du_lieu_tang_truong_gdp_quy.csv'), 'utf8'));
  const quarterTimeColumn = quarterSource[0]?.indexOf('thoi_gian') ?? -1;
  const latestQuarter = quarterTimeColumn < 0 ? null : quarterSource.slice(1).map(row => row[quarterTimeColumn]).filter(Boolean).sort().at(-1);
  await writeFile(path.join(OUT, 'refresh_manifest.json'), JSON.stringify({
    retrieved_at_utc: new Date().toISOString(),
    data_cutoff: { annual_gdp: years.at(-1), quarterly_gdp_growth: latestQuarter, cpi: latestCpiPeriod.slice(0, 7), cpi_official_release: latestReportedCpi?.[0]?.slice(0, 7) },
    sources: {
      world_bank_api: 'https://api.worldbank.org/v2/country/VNM/indicator/{indicator}?date=1985:2026&format=json&per_page=1000',
      nso_quarterly_gdp_2026: 'https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/',
      nso_pxweb_cpi: pxUrl,
      nso_cpi_release_archive: cpiReleaseArchiveUrl,
      nso_cpi_latest_release: latestCpiReleaseUrl,

    },
    indicators: wbIds,
    notes: {
      quarterly_gdp_2026: 'NSO quarterly year-on-year estimates for Q1-Q3 2026, from the official Q3 and first-nine-months release; not GDP level observations.',
      sectors: 'World Bank NV.AGR.TOTL.CD, NV.IND.TOTL.CD, NV.SRV.TOTL.CD; definitions are broad value-added groups.',
      monthly_gdp: 'Cubic spline is only a compatibility series for the current dashboard; do not use it as observed monthly GDP in backtests.',
      cpi_monthly: 'NSO PXWeb E11.07 index observations and monthly CPI release rates are stored separately. Release rates are copied as published; never converted into index levels or backfilled across base changes.',
      quarterly_gdp_refresh: 'Quarterly GDP growth is a separate NSO release series and is not rewritten by the annual World Bank updater.'
    }
  }, null, 2), 'utf8');
  console.log(`Wrote ${years.length} annual rows (latest ${years.at(-1)}), ${monthIndex} compatibility spline rows, and ${cpiRows.length - 1} CPI index rows through ${latestCpiPeriod}, plus ${allReleases.length} official monthly release-rate rows through ${latestReportedCpi?.[0] ?? 'unknown'} to ${OUT}`);
}

await main();
