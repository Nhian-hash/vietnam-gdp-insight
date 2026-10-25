import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { dataPath } from './data_paths.mjs';

const OUT = path.dirname(fileURLToPath(import.meta.url));
const RAW_NSO = path.join(OUT, 'data', 'nso', 'raw');
const SRC = path.join(RAW_NSO, 'pxweb');
const MONTHLY_SOURCE_DIR = path.join(RAW_NSO, 'monthly');
const RAW_IMF = path.join(OUT, 'data', 'imf', 'raw');
await Promise.all([mkdir(SRC, { recursive: true }), mkdir(MONTHLY_SOURCE_DIR, { recursive: true }), mkdir(RAW_IMF, { recursive: true })]);

async function writeDataset(name, content, encoding = 'utf8') {
  await writeFile(await dataPath(name, { forWrite: true }), content, encoding);
}

const monthlyWorkbookSources = [
  ['E01-2026-7.xls', 'https://www.nso.gov.vn/wp-content/uploads/2026/03/E01-2026-7.xls'],
  ['E02-2026-7.xls', 'https://www.nso.gov.vn/wp-content/uploads/2026/03/E02-2026-7.xls'],
  ['IIP-Eng9.xlsx', 'https://www.nso.gov.vn/wp-content/uploads/2026/10/IIP-Eng9.xlsx'],
];
for (const [name, url] of monthlyWorkbookSources) {
  const response = await fetch(url, { signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(`NSO workbook HTTP ${response.status}: ${url}`);
  await writeFile(path.join(MONTHLY_SOURCE_DIR, name), new Uint8Array(await response.arrayBuffer()));
}

function csvCell(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '';
  const s = String(value);
  return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}
function makeCsv(rows) { return rows.map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n'; }
function num(value) {
  if (value === null || value === undefined || String(value).trim() === '' || String(value).trim() === '..') return null;
  const v = Number(String(value).replaceAll(',', '').trim());
  return Number.isFinite(v) ? v : null;
}
function fmt(value, digits = 6) { return value === null || value === undefined || !Number.isFinite(Number(value)) ? '' : Number(Number(value).toFixed(digits)).toString(); }
function norm(value) { return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().replace(/\s+/g, ' '); }
function slug(value) { return norm(value).replaceAll(' ', '_'); }
function parseCsv(text) {
  const rows = []; let row = [], cell = '', quoted = false; text = text.replace(/^\uFEFF/, '');
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) { if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') quoted = false; else cell += c; }
    else if (c === '"') quoted = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n') { row.push(cell.replace(/\r$/, '')); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell.length || row.length) { row.push(cell.replace(/\r$/, '')); rows.push(row); }
  return rows;
}
function htmlAttrs(tag) { return Object.fromEntries([...tag.matchAll(/([\w:$-]+)="([^"]*)"/g)].map(m => [m[1].toLowerCase(), m[2]])); }
async function fetchPxWebCsv(url) {
  const page = await fetch(url, { headers: { 'user-agent': 'Mozilla/5.0 (compatible; Vietnam-GDP-data-refresh/1.0)' }, signal: AbortSignal.timeout(30000) });
  if (!page.ok) throw new Error(`PXWeb page HTTP ${page.status}: ${url}`);
  const html = await page.text(); const form = new URLSearchParams();
  for (const match of html.matchAll(/<input\b[^>]*>/gis)) { const a = htmlAttrs(match[0]); if (a.name && a.type?.toLowerCase() === 'hidden') form.append(a.name, a.value ?? ''); }
  const selects = [...html.matchAll(/<select\b[^>]*>[\s\S]*?<\/select>/gi)].map(m => ({ tag: m[0], attrs: htmlAttrs(m[0].match(/<select\b[^>]*>/i)?.[0] ?? '') }));
  for (const s of selects) {
    const name = s.attrs.name; if (!name || name.includes('cboSelectLanguages') || name.includes('OutputFormatDropDownList')) continue;
    for (const option of s.tag.matchAll(/<option\b[^>]*value="([^"]*)"/gi)) form.append(name, option[1]);
  }
  const format = selects.find(s => s.attrs.name?.includes('OutputFormatDropDownList'));
  if (!format) throw new Error(`PXWeb CSV selector missing: ${url}`);
  form.set(format.attrs.name, 'FileTypeCsvWithHeadingAndComma');
  form.set('ctl00$ContentPlaceHolderMain$VariableSelector1$VariableSelector1$ButtonViewTable', 'Continue');
  const cookie = (page.headers.get('set-cookie') ?? '').split(';')[0];
  const response = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', cookie, 'user-agent': 'Mozilla/5.0 (compatible; Vietnam-GDP-data-refresh/1.0)' }, body: form.toString(), redirect: 'follow', signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(`PXWeb CSV HTTP ${response.status}: ${url}`);
  const text = await response.text();
  if (text.length < 1000) throw new Error(`PXWeb returned an empty table: ${url}`);
  return text;
}
async function saveSource(name, text) { await writeFile(path.join(SRC, name), text, 'utf8'); return parseCsv(text); }
function rowByHeader(rows, predicate) { return rows.findIndex(r => predicate(r)); }
function yearNum(value) { const match = String(value ?? '').match(/(?:19|20)\d{2}/); return match ? Number(match[0]) : null; }
function statusForYear(year, label = '') {
  const text = `${label}`.toLowerCase();
  if (text.includes('est')) return 'uoc_tinh';
  if (text.includes('prel')) return 'so_bo';
  if (year >= 2025) return 'uoc_tinh';
  if (year === 2024) return 'so_bo';
  return 'chinh_thuc_theo_bang_nguon';
}

const tableUrls = {
  nso_gdp_sectors: 'https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.02.px/',
  nso_grdp_pc: 'https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.12.px/',
  nso_grdp_growth: 'https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.10.px/',
  nso_population: 'https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.03-07.px/',
  nso_trade_annual: 'https://pxweb.nso.gov.vn/pxweb/en/E%2009.%20IMEX/E%2009.%20IMEX__Px_E_09/E09.01.px/',
  nso_retail_annual: 'https://pxweb.nso.gov.vn/pxweb/en/E%2008.%20Trade/E%2008.%20Trade__Px_E_08/E08.01.px/',
  nso_fdi_annual: 'https://pxweb.nso.gov.vn/pxweb/en/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/E04.11.px/',
  nso_iip_annual: 'https://pxweb.nso.gov.vn/pxweb/en/E%2007.%20Industry/E%2007.%20Industry__Px_E_07/E07.01.px/',
};

const names = {
  'red river delta': ['Đồng bằng sông Hồng', 'R1'],
  'northern midlands and mountain areas': ['Trung du và miền núi phía Bắc', 'R2'],
  'north central and central coastal areas': ['Bắc Trung Bộ và Duyên hải miền Trung', 'R3'],
  'central highlands': ['Tây Nguyên', 'R4'],
  'south east': ['Đông Nam Bộ', 'R5'],
  'mekong river delta': ['Đồng bằng sông Cửu Long', 'R6'],
  'ha noi': ['Hà Nội'], 'vinh phuc': ['Vĩnh Phúc'], 'bac ninh': ['Bắc Ninh'], 'quang ninh': ['Quảng Ninh'],
  'hai duong': ['Hải Dương'], 'hai phong': ['Hải Phòng'], 'hung yen': ['Hưng Yên'], 'thai binh': ['Thái Bình'],
  'ha nam': ['Hà Nam'], 'nam dinh': ['Nam Định'], 'ninh binh': ['Ninh Bình'], 'ha giang': ['Hà Giang'],
  'cao bang': ['Cao Bằng'], 'bac kan': ['Bắc Kạn'], 'tuyen quang': ['Tuyên Quang'], 'lao cai': ['Lào Cai'],
  'yen bai': ['Yên Bái'], 'thai nguyen': ['Thái Nguyên'], 'lang son': ['Lạng Sơn'], 'bac giang': ['Bắc Giang'],
  'phu tho': ['Phú Thọ'], 'dien bien': ['Điện Biên'], 'lai chau': ['Lai Châu'], 'son la': ['Sơn La'], 'hoa binh': ['Hòa Bình'],
  'thanh hoa': ['Thanh Hóa'], 'nghe an': ['Nghệ An'], 'ha tinh': ['Hà Tĩnh'], 'quang binh': ['Quảng Bình'],
  'quang tri': ['Quảng Trị'], 'thua thien hue': ['Thừa Thiên Huế'], 'da nang': ['Đà Nẵng'], 'quang nam': ['Quảng Nam'],
  'quang ngai': ['Quảng Ngãi'], 'binh dinh': ['Bình Định'], 'phu yen': ['Phú Yên'], 'khanh hoa': ['Khánh Hòa'],
  'ninh thuan': ['Ninh Thuận'], 'binh thuan': ['Bình Thuận'], 'kon tum': ['Kon Tum'], 'gia lai': ['Gia Lai'],
  'dak lak': ['Đắk Lắk'], 'dak nong': ['Đắk Nông'], 'lam dong': ['Lâm Đồng'], 'binh phuoc': ['Bình Phước'],
  'tay ninh': ['Tây Ninh'], 'binh duong': ['Bình Dương'], 'dong nai': ['Đồng Nai'], 'ba ria vung tau': ['Bà Rịa - Vũng Tàu'],
  'ho chi minh city': ['TP. Hồ Chí Minh'], 'long an': ['Long An'], 'tien giang': ['Tiền Giang'], 'ben tre': ['Bến Tre'],
  'tra vinh': ['Trà Vinh'], 'vinh long': ['Vĩnh Long'], 'dong thap': ['Đồng Tháp'], 'an giang': ['An Giang'],
  'kien giang': ['Kiên Giang'], 'can tho': ['Cần Thơ'], 'hau giang': ['Hậu Giang'], 'soc trang': ['Sóc Trăng'],
  'bac lieu': ['Bạc Liêu'], 'ca mau': ['Cà Mau'],
};

const tables = {};
await Promise.all(Object.entries(tableUrls).map(async ([key, url]) => {
  const text = await fetchPxWebCsv(url);
  tables[key] = await saveSource(`${key}.csv`, text);
}));

// National GDP by sector, NSO current-price series (billion VND).
const gdpRows = tables.nso_gdp_sectors;
const gdpHeaderIdx = rowByHeader(gdpRows, r => norm(r[0]) === 'year' && r.some(c => norm(c).includes('agriculture forestry and fishing')));
if (gdpHeaderIdx < 0) throw new Error('NSO GDP sector header not found');
const gdpHeader = gdpRows[gdpHeaderIdx];
const findCol = text => gdpHeader.findIndex(h => norm(h).includes(norm(text)));
const gdpCols = {
  total: findCol('total (bill dongs) total'), agriculture: findCol('agriculture forestry and fishing'),
  industry: findCol('industry and construction'), services: findCol('services'), taxes: findCol('taxes less subsidies on products'),
  totalShare: findCol('structure total'), agricultureShare: findCol('structure agriculture'),
  industryShare: findCol('structure industry'), servicesShare: findCol('structure services'), taxesShare: findCol('structure taxes'),
};
const gdpSectorRecords = [];
for (const row of gdpRows.slice(gdpHeaderIdx + 1)) {
  const year = yearNum(row[0]); if (!year) continue;
  const record = { year, total: num(row[gdpCols.total]), agri: num(row[gdpCols.agriculture]), industry: num(row[gdpCols.industry]), services: num(row[gdpCols.services]), taxes: num(row[gdpCols.taxes]), shares: [gdpCols.agricultureShare, gdpCols.industryShare, gdpCols.servicesShare, gdpCols.taxesShare].map(i => num(row[i])) };
  gdpSectorRecords.push(record);
}
gdpSectorRecords.sort((a, b) => a.year - b.year);
const sectorOut = [['nam','tong_gdp_vnd_ty','gdp_nong_lam_thuy_san_vnd_ty','gdp_cong_nghiep_xay_dung_vnd_ty','gdp_dich_vu_vnd_ty','thue_san_pham_tru_tro_cap_vnd_ty','ty_trong_nong_lam_thuy_san_pct','ty_trong_cong_nghiep_xay_dung_pct','ty_trong_dich_vu_pct','ty_trong_thue_san_pham_pct','tang_truong_gdp_nong_lam_thuy_san_yoy_pct','tang_truong_gdp_cong_nghiep_xay_dung_yoy_pct','tang_truong_gdp_dich_vu_yoy_pct','trang_thai']];
for (let i = 0; i < gdpSectorRecords.length; i++) {
  const r = gdpSectorRecords[i], prev = gdpSectorRecords[i - 1];
  const growth = (x, p) => x !== null && p !== null && p !== 0 ? (x / p - 1) * 100 : null;
  sectorOut.push([r.year, fmt(r.total,2),fmt(r.agri,2),fmt(r.industry,2),fmt(r.services,2),fmt(r.taxes,2),...r.shares.map(v=>fmt(v,4)),fmt(growth(r.agri,prev?.agri ?? null),4),fmt(growth(r.industry,prev?.industry ?? null),4),fmt(growth(r.services,prev?.services ?? null),4),statusForYear(r.year)]);
}
await writeDataset('du_lieu_gdp_co_cau_3_nganh.csv', makeCsv(sectorOut));

// Combine observed WB USD GDP with the NSO nominal GDP in local currency.
const annualWB = parseCsv(await readFile(await dataPath('GDP_Vietnam_Annual.csv'),'utf8'));
const realWB = parseCsv(await readFile(await dataPath('du_lieu_gdp_thuc_va_tang_truong.csv'),'utf8'));
const wbH = annualWB[0], realH = realWB[0];
const annualMap = new Map(annualWB.slice(1).map(r=>[Number(r[wbH.indexOf('Year')]),r]));
const realMap = new Map(realWB.slice(1).map(r=>[Number(r[realH.indexOf('nam')]),r]));
const vndMap = new Map(gdpSectorRecords.map(r=>[r.year,r]));
const totalOut = [['nam','gdp_danh_nghia_usd','gdp_danh_nghia_vnd_ty','gdp_thuc_usd_2015','tang_truong_gdp_thuc_pct','trang_thai_usd','trang_thai_vnd','ghi_chu']];
for (const year of [...annualMap.keys()].sort((a,b)=>a-b)) {
  const a=annualMap.get(year), rr=realMap.get(year), v=vndMap.get(year);
  totalOut.push([year,fmt(num(a[wbH.indexOf('GDP_USD')]),2),fmt(v?.total,2),fmt(num(rr?.[realH.indexOf('gdp_thuc_usd_2015')]),2),fmt(num(rr?.[realH.indexOf('tang_truong_gdp_thuc_pct')]),4),year===2025?'World Bank, mới nhất':'World Bank',v?statusForYear(year):'',year===2025?'GDP danh nghĩa USD và GDP thực constant 2015; GDP VND theo GSO current prices':'' ]);
}
await writeDataset('du_lieu_gdp_tong_hop.csv', makeCsv(totalOut));

// IMF monthly average exchange rate: domestic currency units per USD.
const fxUrl = 'https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/ER/+/VNM.XDC_USD.PA_RT.M?startPeriod=1980-01&endPeriod=2026-12&format=jsondata';
const fxResponse = await fetch(fxUrl, { signal: AbortSignal.timeout(30000) });
if (!fxResponse.ok) throw new Error(`IMF ER API HTTP ${fxResponse.status}`);
const fxJson = await fxResponse.json();
await writeFile(path.join(RAW_IMF,'imf_er_vnm_monthly_response.json'), JSON.stringify(fxJson), 'utf8');
const fxStruct = fxJson.data?.structures?.[0], fxSeries = Object.values(fxJson.data?.dataSets?.[0]?.series ?? {})[0];
if (!fxStruct || !fxSeries) throw new Error('IMF ER response missing data structure');
const fxPeriods = fxStruct.dimensions.observation[0].values.map(x=>x.value);
const fxObs = fxSeries.observations ?? {};
const fxOut = [['thoi_gian','ty_gia_usd_vnd','tan_suat','loai_ty_gia','ma_chuoi_imf','trang_thai']];
for (let i=0;i<fxPeriods.length;i++) {
  const m=String(fxPeriods[i]).match(/^(\d{4})-M(\d{2})$/); if(!m) continue;
  const raw=fxObs[String(i)]?.[0], value=num(raw); if(value===null) continue;
  fxOut.push([`${m[1]}-${m[2]}-01`,fmt(value,6),'thang','binh_quan_ky','VNM.XDC_USD.PA_RT.M','IMF_observed']);
}
await writeDataset('du_lieu_ty_gia_usd_vnd.csv',makeCsv(fxOut));

// Historical annual CPI inflation from World Bank WDI, separate from the monthly NSO index.
const cpiWdiUrl='https://api.worldbank.org/v2/country/VNM/indicator/FP.CPI.TOTL.ZG?date=1980:2026&format=json&per_page=1000';
const cpiResp=await fetch(cpiWdiUrl,{signal:AbortSignal.timeout(30000)}); if(!cpiResp.ok) throw new Error(`WDI CPI HTTP ${cpiResp.status}`);
const cpiBody=await cpiResp.json();
const cpiAnnual=[['nam','lam_phat_cpi_yoy_pct','ma_chi_tieu','nguon','trang_thai']];
for(const r of cpiBody[1]??[]) if(r.value!==null) cpiAnnual.push([Number(r.date),fmt(Number(r.value),6),'FP.CPI.TOTL.ZG','World Bank WDI',Number(r.date)>=2025?'moi_nhat_trong_wdi':'chinh_thuc_theo_wdi']);
await writeDataset('du_lieu_lam_phat_cpi_nam_lich_su.csv',makeCsv(cpiAnnual));

// Long-form annual merchandise trade from NSO PXWeb (unit in source: million USD).
const tradeRows=tables.nso_trade_annual;
const tradeAnnual=[];
for(const r of tradeRows){const year=yearNum(r[1]);if(!year||!norm(r[0]).startsWith('value'))continue;tradeAnnual.push({year,total:num(r[2]),exports:num(r[3]),imports:num(r[4]),balance:num(r[5])});}
tradeAnnual.sort((a,b)=>a.year-b.year);
const tradeOut=[['nam','tong_kim_ngach_xuat_nhap_khau_usd','kim_ngach_xuat_khau_usd','kim_ngach_nhap_khau_usd','can_can_thuong_mai_usd','tan_suat','trang_thai','don_vi_nguon']];
for(const r of tradeAnnual) tradeOut.push([r.year,fmt(r.total*1e6,0),fmt(r.exports*1e6,0),fmt(r.imports*1e6,0),fmt(r.balance*1e6,0),'nam',statusForYear(r.year), 'million_USD_converted_to_USD']);
await writeDataset('du_lieu_xuat_nhap_khau.csv',makeCsv(tradeOut));

// Annual total retail sales (billions of VND) from the NSO table.
const retailRows=tables.nso_retail_annual;
const retailAnnual=[];
for(const r of retailRows){const year=yearNum(r[1]);if(!year||!norm(r[0]).startsWith('value'))continue;retailAnnual.push({year,total:num(r[2]),retail:num(r[3]),food:num(r[4]),services:num(r[5])});}
retailAnnual.sort((a,b)=>a.year-b.year);
const retailOut=[['nam','tong_muc_ban_le_vnd','ban_le_hang_hoa_vnd','luu_tru_an_uong_vnd','dich_vu_du_lich_vnd','tan_suat','trang_thai','don_vi_nguon']];
for(const r of retailAnnual) retailOut.push([r.year,fmt(r.total*1e9,0),fmt(r.retail*1e9,0),fmt(r.food*1e9,0),fmt(r.services*1e9,0),'nam',statusForYear(r.year),'billion_VND_converted_to_VND']);
await writeDataset('du_lieu_ban_le_tieu_dung.csv',makeCsv(retailOut));

// FDI projects licensed and implementation capital by year, NSO table E04.11.
const fdiRows=tables.nso_fdi_annual;
const fdiOut=[['nam','so_du_an_fdi_duoc_cap_phep','von_dang_ky_du_an_fdi_usd','von_fdi_thuc_hien_usd','tan_suat','trang_thai','dinh_nghia_von_dang_ky']];
for(const r of fdiRows){if(!/^\s*(?:19|20)\d{2}\s*$/.test(String(r[0]??'')))continue;const year=yearNum(r[0]);if(!year)continue;fdiOut.push([year,fmt(num(r[1]),0),fmt(num(r[2])*1e6,0),fmt(num(r[3])*1e6,0),'nam',statusForYear(year),'von dang ky dự án cấp phép; triệu USD được đổi sang USD']);}
await writeDataset('du_lieu_fdi_dau_tu.csv',makeCsv(fdiOut));
const fdiEarly=fdiRows.find(r=>/^\s*1988\s*[-–]\s*1990\s*$/.test(String(r[0]??'')));
if(fdiEarly) await writeDataset('du_lieu_fdi_giai_doan_1988_1990.csv',makeCsv([
  ['giai_doan','so_du_an_fdi_duoc_cap_phep','von_dang_ky_du_an_fdi_usd','von_fdi_thuc_hien_usd','tan_suat','trang_thai','ghi_chu'],
  ['1988-1990',fmt(num(fdiEarly[1]),0),fmt(num(fdiEarly[2])*1e6,0),fmt(num(fdiEarly[3])*1e6,0),'3_nam_gop','chinh_thuc_theo_bang_nguon','Nguồn chỉ công bố gộp giai đoạn; không phân bổ thành các năm riêng.'],
]));
const fdi2026=[['thoi_gian','nam','ky_bao_cao','von_fdi_dang_ky_tong_hop_usd','von_fdi_thuc_hien_luy_ke_usd','tang_truong_dang_ky_yoy_pct','tang_truong_thuc_hien_yoy_pct','trang_thai','dinh_nghia'],['2026-09-30',2026,'9_thang',50360000000,21070000000,76.4,12.1,'uoc_tinh_luy_ke_chinh_thuc','Đăng ký gồm cấp mới + điều chỉnh + góp vốn/mua cổ phần; giải ngân lũy kế']];
await writeDataset('du_lieu_fdi_luy_ke_2026.csv',makeCsv(fdi2026));

// Historical industrial production index (index vs previous year = 100), by activity and year.
const iipRows=tables.nso_iip_annual;
const iipHeadIdx=rowByHeader(iipRows,r=>norm(r[0])==='industrial activity'&&r.some(x=>String(x).match(/^20\d{2}$/)));
if(iipHeadIdx<0) throw new Error('NSO annual IIP table header not found');
const iipYears=iipRows[iipHeadIdx].slice(1).map(yearNum);
const iipAnnual=[['nam','ten_nganh','chi_so_iip_truoc_nam_100','tang_truong_iip_yoy_pct','tan_suat','trang_thai']];
for(const row of iipRows.slice(iipHeadIdx+1)){
  const activity=String(row[0]??'').trim(); if(!activity||norm(activity)==='industry activity')continue;
  for(let j=0;j<iipYears.length;j++){const year=iipYears[j],idx=num(row[j+1]);if(!year||idx===null)continue;iipAnnual.push([year,activity,fmt(idx,4),fmt(idx-100,4),'nam',year===2025?'uoc_tinh':'chinh_thuc_theo_bang_nguon']);}
}
await writeDataset('du_lieu_san_xuat_iip_nam.csv',makeCsv(iipAnnual));

// GRDP 63 historical provinces + six statistical regions, 2018-2025.
const pcRows=tables.nso_grdp_pc, popRows=tables.nso_population, growthRows=tables.nso_grdp_growth;
const pcHeadIdx=rowByHeader(pcRows,r=>norm(r[0])==='cities provincies'&&r.some(x=>norm(x).includes('est 2025')));
const popHeadIdx=rowByHeader(popRows,r=>norm(r[0])==='cities provincies'&&r.some(x=>norm(x)==='total prel 2025'));
const grHeadIdx=rowByHeader(growthRows,r=>norm(r[0])==='cities provincies'&&r.some(x=>norm(x).includes('est 2025')));
if(pcHeadIdx<0||popHeadIdx<0||grHeadIdx<0) throw new Error('GRDP, population or GRDP growth header not found');
const pcYears=pcRows[pcHeadIdx].slice(1).map(yearNum), grYears=growthRows[grHeadIdx].slice(1).map(yearNum);
const popTotalCols=new Map();
for(let i=1;i<popRows[popHeadIdx].length;i++){const h=norm(popRows[popHeadIdx][i]);const y=yearNum(h);if(h.startsWith('total ')&&y)popTotalCols.set(y,i);}
const dataMap=rows=>new Map(rows.slice(3).filter(r=>r[0]).map(r=>[norm(r[0]),r]));
const popMap=dataMap(popRows), growthMap=dataMap(growthRows);
// NSO population table has renamed Hue and uses a different label for region R3.
// Canonicalize those two labels so legacy GRDP geography is retained for every year.
const popAliases=new Map([
  ['thua thien hue','hue'],
  ['north central and central coastal areas','northern central area and central coastal area'],
]);
const populationFor=key=>popMap.get(key)??popMap.get(popAliases.get(key)??key);
const regionNames=new Map([
  ['red river delta',['Đồng bằng sông Hồng','R1']],['northern midlands and mountain areas',['Trung du và miền núi phía Bắc','R2']],
  ['north central and central coastal areas',['Bắc Trung Bộ và Duyên hải miền Trung','R3']],['central highlands',['Tây Nguyên','R4']],
  ['south east',['Đông Nam Bộ','R5']],['mekong river delta',['Đồng bằng sông Cửu Long','R6']],
]);
const grdpOut=[['ma_tinh','ten_tinh','ten_tinh_nguon','ma_vung_kinh_te','ten_vung_kinh_te','loai_dia_ban','nam','quy_mo_grdp_vnd','grdp_binh_quan_dau_nguoi_trieu_vnd','dan_so_binh_quan_nghin_nguoi','tang_truong_grdp_yoy_pct','trang_thai']];
let currentRegion=null;
for(const row of pcRows.slice(pcHeadIdx+1)){
  const sourceName=String(row[0]??'').trim(); if(!sourceName)continue;
  const key=norm(sourceName); if(regionNames.has(key)){currentRegion={key,label:regionNames.get(key)[0],code:regionNames.get(key)[1]};}
  if(key==='whole country')continue;
  const isRegion=regionNames.has(key); const mapped=names[key]; const vietnamese=mapped?.[0]??sourceName;
  const region=isRegion?{key,label:vietnamese,code:regionNames.get(key)[1]}:currentRegion;
  const populationRow=populationFor(key), growthRow=growthMap.get(key);
  for(let j=0;j<pcYears.length;j++){
    const year=pcYears[j],pc=num(row[j+1]),popCol=popTotalCols.get(year),pop=populationRow&&popCol!==undefined?num(populationRow[popCol]):null;
    if(!year||pc===null||pop===null)continue;
    const growthCol=growthRows[grHeadIdx].findIndex(h=>yearNum(h)===year);
    const grdpIndex=growthRow&&growthCol>0?num(growthRow[growthCol]):null;
    const id=isRegion?`REG_${region.code}`:`legacy63_${slug(sourceName)}`;
    grdpOut.push([isRegion?'':id,vietnamese,sourceName,region?.code??'',region?.label??'',isRegion?'vung_thong_ke':'tinh_thanh_63_truyen_thong',year,fmt(pc*pop,2),fmt(pc,4),fmt(pop,3),grdpIndex===null?'':fmt(grdpIndex-100,4),year===2025?'uoc_tinh':year===2024?'so_bo':'chinh_thuc_theo_bang_nguon']);
  }
}
const grdpRecords=grdpOut.slice(1);
const provinceYears=new Set(grdpRecords.filter(r=>r[5]==='tinh_thanh_63_truyen_thong').map(r=>r[1]+'|'+r[6]));
const regionYears=new Set(grdpRecords.filter(r=>r[5]==='vung_thong_ke').map(r=>r[4]+'|'+r[6]));
const provinceNames=new Set(grdpRecords.filter(r=>r[5]==='tinh_thanh_63_truyen_thong').map(r=>r[1]));
const regionLabels=new Set(grdpRecords.filter(r=>r[5]==='vung_thong_ke').map(r=>r[4]));
if(provinceNames.size!==63||regionLabels.size!==6||provinceYears.size!==63*pcYears.filter(Boolean).length||regionYears.size!==6*pcYears.filter(Boolean).length){
  throw new Error(`GRDP coverage check failed: provinces=${provinceNames.size}, regions=${regionLabels.size}, province rows=${provinceYears.size}, region rows=${regionYears.size}`);
}
await writeDataset('du_lieu_grdp_63_tinh_thanh.csv',makeCsv(grdpOut));

// Latest monthly retail estimates from official NSO monthly releases; values are current-price estimates.
const retailMonthly=[
  ['thoi_gian','tong_muc_ban_le_vnd','tang_truong_danh_nghia_yoy_pct','tang_truong_thuc_yoy_luy_ke_pct','tan_suat','trang_thai','nguon'],
  ['2026-01-01',632400000000000,9.3,6.3,'thang','uoc_tinh_chinh_thuc','NSO monthly report Jan 2026'],
  ['2026-02-01',613700000000000,8.5,4.5,'thang','uoc_tinh_chinh_thuc','NSO monthly report Feb 2026; real growth is cumulative Jan-Feb'],
  ['2026-03-01',638600000000000,12.1,7.0,'thang','uoc_tinh_chinh_thuc','NSO Q1 2026 report; real growth is cumulative Q1'],
  ['2026-04-01',646300000000000,12.1,6.3,'thang','uoc_tinh_chinh_thuc','NSO monthly report Apr 2026; real growth is cumulative Jan-Apr'],
  ['2026-05-01',647100000000000,11.8,6.1,'thang','uoc_tinh_chinh_thuc','NSO monthly report May 2026; real growth is cumulative Jan-May'],
  ['2026-06-01',665600000000000,14.8,7.3,'thang','uoc_tinh_chinh_thuc','NSO Q2 2026 report; real growth is cumulative first half'],
  ['2026-07-01',669100000000000,14.5,7.5,'thang','uoc_tinh_chinh_thuc','NSO monthly report Jul 2026; real growth is cumulative Jan-Jul'],
  ['2026-08-01',679800000000000,14.9,7.6,'thang','uoc_tinh_chinh_thuc','NSO monthly report Aug 2026; real growth is cumulative Jan-Aug'],
  ['2026-09-01',690600000000000,14.1,7.8,'thang','uoc_tinh_chinh_thuc','NSO/MOIT Sep 2026 release; real growth is cumulative Jan-Sep'],
];
await writeDataset('du_lieu_ban_le_tieu_dung_thang_2026.csv',makeCsv(retailMonthly));

const manifestPath=path.join(OUT,'refresh_manifest.json');
let manifest={};try{manifest=JSON.parse(await readFile(manifestPath,'utf8'));}catch{}
manifest.retrieved_at_utc=new Date().toISOString();
manifest.data_cutoff={...(manifest.data_cutoff??{}),fx_monthly:'2026-07',grdp_local:'2018-2025',trade_annual:tradeAnnual.at(-1)?.year,trade_monthly:'2026-09',retail_annual:retailAnnual.at(-1)?.year,retail_monthly:'2026-09',fdi_annual:2025,fdi_latest:'2026-09',iip_annual:iipYears.at(-1),iip_monthly:'2026-09',cpi_annual_wdi:Math.max(...(cpiBody[1]??[]).filter(x=>x.value!==null).map(x=>Number(x.date)))};
manifest.sources={...(manifest.sources??{}),nso_pxweb:tableUrls,imf_er_monthly:fxUrl,world_bank_cpi_annual:cpiWdiUrl,nso_fdi_2026:'https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/',nso_iip_monthly_file:'https://www.nso.gov.vn/wp-content/uploads/2026/10/IIP-Eng9.xlsx',nso_trade_monthly_2026_files:['https://www.nso.gov.vn/wp-content/uploads/2026/03/E01-2026-7.xls','https://www.nso.gov.vn/wp-content/uploads/2026/03/E02-2026-7.xls'],nso_retail_monthly_2026_reports:['https://www.nso.gov.vn/en/highlight/2026/03/report-socio-economic-performance-in-january-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/03/report-socio-economic-performance-in-february-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/04/report-on-socio-economic-situation-in-quarter-i-in-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/07/report-on-socio-economic-situation-in-april-and-four-months-of-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/06/report-on-socio-economic-situation-in-may-and-five-months-of-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/08/report-socio-economic-performance-in-second-quarter-and-the-first-half-of-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/08/report-socio-economic-performance-in-july-and-7-months-of-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/09/report-socio-economic-performance-in-august-and-8-months-of-2026/','https://www.nso.gov.vn/en/data-and-statistics/2026/10/report-socio-economic-performance-in-third-quarter-and-nine-months-of-2026/']};
manifest.notes={...(manifest.notes??{}),fx_monthly:'IMF ER monthly average rate in VND per USD; latest observed period in this refresh is July 2026.',grdp_local:'GRDP levels derived from NSO GRDP per-capita (million VND/person) multiplied by NSO average population (thousand persons), yielding billion VND. The six region aggregates are shown beside their constituent provinces; do not sum both levels.',trade_frequency:'Historical merchandise trade is annual through the latest NSO table year; 2026 monthly preliminary exports and imports are supplied separately in du_lieu_xuat_nhap_khau_thang_2026.csv.',retail_frequency:'Historical retail is annual; the 2026 monthly file contains monthly estimates and official cumulative real growth rates. The cumulative real growth column is not a monthly rate.',iip_frequency:'Annual IIP uses prior-year=100 indexes (2012-2025); 2026 monthly IIP uses 2015=100. These are separate grains and bases.',fdi_comparability:'Annual NSO E04.11 observations begin in 1991 because the source groups 1988-1990 into one three-year total stored separately in du_lieu_fdi_giai_doan_1988_1990.csv. Historical registered capital is licensed project capital; the 2026 cumulative registered total includes new registration, adjustments, and capital contributions/share purchases, so those definitions are not directly comparable.',modeling:'Never use cubic-spline monthly GDP values as observed targets for ADF, training, or test metrics. Forecast evaluation uses observed annual real GDP only.'};
await writeFile(manifestPath,JSON.stringify(manifest,null,2),'utf8');
console.log(`Wrote FX ${fxOut.length-1}, GDP sectors ${sectorOut.length-1}, trade annual ${tradeOut.length-1}, retail annual ${retailOut.length-1}, GRDP ${grdpOut.length-1}, FDI annual ${fdiOut.length-1}, annual IIP rows ${iipAnnual.length-1}.`);
