import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SOURCE_DIR = path.join(ROOT, 'data', 'nso', 'raw', 'expanded');
const WORLD_BANK_SOURCE_DIR = path.join(ROOT, 'data', 'world_bank', 'raw', 'expanded');
await Promise.all([mkdir(SOURCE_DIR, { recursive: true }), mkdir(WORLD_BANK_SOURCE_DIR, { recursive: true })]);

const NSO = 'https://pxweb.nso.gov.vn/pxweb/en';
const tables = {
  gdp_constant_sector: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.03.px/`,
  gdp_current_activity: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.04-05.px/`,
  gdp_constant_growth_activity: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.06-07.px/`,
  gdp_current_expenditure: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.08.px/`,
  gdp_constant_expenditure: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.09.px/`,
  budget_revenue: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.13-14.px/`,
  budget_expenditure: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.16.px/`,
  credit_outstanding: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.19.px/`,
  balance_of_payments: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.20.px/`,
  interest_rates: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.21.px/`,
  tfp_contribution: `${NSO}/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.27.px/`,
  employment_activity: `${NSO}/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.42.px/?rxid=cca2c8f0-bcd4-424c-8b1d-672327579c1a`,
  labor_productivity: `${NSO}/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.57.px/?rxid=cca2c8f0-bcd4-424c-8b1d-672327579c1a`,
  unemployment_region: `${NSO}/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.59.px/?rxid=cca2c8f0-bcd4-424c-8b1d-672327579c1a`,
  investment_ownership: `${NSO}/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/E04.01.px/`,
  investment_constant_industry: `${NSO}/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/E04.04.px/`,
};

function attrs(tag) {
  return Object.fromEntries([...tag.matchAll(/([\w:$-]+)="([^"]*)"/g)].map(m => [m[1].toLowerCase(), m[2]]));
}

async function fetchCsv(url) {
  let last;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const page = await fetch(url, {
        headers: { 'user-agent': 'Mozilla/5.0 (compatible; Vietnam-GDP-thesis-data-refresh/1.0)' },
        signal: AbortSignal.timeout(60000),
      });
      if (!page.ok) throw new Error(`PXWeb page HTTP ${page.status}`);
      const html = await page.text();
      const form = new URLSearchParams();
      for (const m of html.matchAll(/<input\b[^>]*>/gis)) {
        const a = attrs(m[0]);
        if (a.name && a.type?.toLowerCase() === 'hidden') form.append(a.name, a.value ?? '');
      }
      const selects = [...html.matchAll(/<select\b[^>]*>[\s\S]*?<\/select>/gi)].map(m => ({
        tag: m[0], attrs: attrs(m[0].match(/<select\b[^>]*>/i)?.[0] ?? ''),
      }));
      for (const select of selects) {
        const name = select.attrs.name;
        if (!name || name.includes('cboSelectLanguages') || name.includes('OutputFormatDropDownList')) continue;
        for (const option of select.tag.matchAll(/<option\b[^>]*value="([^"]*)"/gi)) form.append(name, option[1]);
      }
      const format = selects.find(s => s.attrs.name?.includes('OutputFormatDropDownList'));
      if (!format) throw new Error('PXWeb CSV selector missing');
      form.set(format.attrs.name, 'FileTypeCsvWithHeadingAndComma');
      form.set('ctl00$ContentPlaceHolderMain$VariableSelector1$VariableSelector1$ButtonViewTable', 'Continue');
      const cookies = (page.headers.get('set-cookie') ?? '').split(/,(?=[^;]+=[^;]+)/).map(x => x.split(';')[0]).filter(Boolean).join('; ');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'content-type': 'application/x-www-form-urlencoded', cookie: cookies,
          'user-agent': 'Mozilla/5.0 (compatible; Vietnam-GDP-thesis-data-refresh/1.0)' },
        body: form.toString(), redirect: 'follow', signal: AbortSignal.timeout(90000),
      });
      if (!response.ok) throw new Error(`PXWeb CSV HTTP ${response.status}`);
      const text = await response.text();
      if (text.length < 80 || !text.includes(',')) throw new Error('PXWeb returned an empty or invalid CSV');
      return text.replace(/\0+$/g, '');
    } catch (error) {
      last = error;
      if (attempt < 3) await new Promise(resolve => setTimeout(resolve, 1200 * attempt));
    }
  }
  throw new Error(`${url}: ${last?.message ?? 'download failed'}`);
}

for (const [name, url] of Object.entries(tables)) {
  const text = await fetchCsv(url);
  const file = `${name}.csv`;
  await writeFile(path.join(SOURCE_DIR, file), text, 'utf8');
  console.log(`${file}: ${Buffer.byteLength(text, 'utf8').toLocaleString()} bytes`);
}

const commodityUrl = 'https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx';
const commodityResponse = await fetch(commodityUrl, { signal: AbortSignal.timeout(90000) });
if (!commodityResponse.ok) throw new Error(`World Bank Pink Sheet HTTP ${commodityResponse.status}: ${commodityUrl}`);
const commodityBytes = new Uint8Array(await commodityResponse.arrayBuffer());
if (commodityBytes.length < 10000) throw new Error('World Bank Pink Sheet response is unexpectedly small');
await writeFile(path.join(WORLD_BANK_SOURCE_DIR, 'world_bank_commodity_monthly.xlsx'), commodityBytes);
console.log(`world_bank_commodity_monthly.xlsx: ${commodityBytes.byteLength.toLocaleString()} bytes`);

const nsoGdpActivityReleaseUrl = 'https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/';
const nsoRelease = await fetch(nsoGdpActivityReleaseUrl, { headers: { 'user-agent': 'Mozilla/5.0 (compatible; Vietnam-GDP-thesis-data-refresh/1.0)' }, signal: AbortSignal.timeout(60000) });
if (!nsoRelease.ok) throw new Error(`NSO release HTTP ${nsoRelease.status}: ${nsoGdpActivityReleaseUrl}`);
const nsoReleaseHtml = await nsoRelease.text();
if (nsoReleaseHtml.length < 5000) throw new Error('NSO quarterly GDP release response is unexpectedly small');
await writeFile(path.join(SOURCE_DIR, 'nso_gdp_activity_q3_2026.html'), nsoReleaseHtml, 'utf8');
console.log(`nso_gdp_activity_q3_2026.html: ${Buffer.byteLength(nsoReleaseHtml, 'utf8').toLocaleString()} bytes`);

const manifest = {
  retrieved_at_utc: new Date().toISOString(),
  method: 'PXWeb CSV download with all table selections; original source responses retained as-is. World Bank Commodity Markets monthly workbook and NSO Q3/9M GDP release page retained as source files.',
  sources: Object.fromEntries(Object.entries(tables).map(([name, url]) => [name, url])),
  world_bank_commodity_monthly: commodityUrl,
  nso_gdp_activity_q3_2026: nsoGdpActivityReleaseUrl,
};
await writeFile(path.join(SOURCE_DIR, 'source_manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
