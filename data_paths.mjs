import { mkdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const PROJECT_ROOT = path.dirname(fileURLToPath(import.meta.url));
const CATALOG_PATH = path.join(PROJECT_ROOT, 'data', 'catalog.json');

async function loadCatalog() {
  try {
    return JSON.parse(await readFile(CATALOG_PATH, 'utf8')).files ?? {};
  } catch (error) {
    if (error.code === 'ENOENT' || error instanceof SyntaxError) return {};
    throw error;
  }
}

export async function dataPath(name, { forWrite = false } = {}) {
  if (path.basename(name) !== name || !/\.(csv|xlsx|xls|json|html)$/i.test(name)) {
    throw new Error(`Expected a dataset filename, got ${name}`);
  }
  const files = await loadCatalog();
  const entry = files[name];
  const target = entry
    ? path.join(PROJECT_ROOT, entry.path)
    : path.join(PROJECT_ROOT, 'data', 'derived', 'generated', name);
  if (forWrite) await mkdir(path.dirname(target), { recursive: true });
  return target;
}
