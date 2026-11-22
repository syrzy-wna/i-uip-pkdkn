#!/usr/bin/env node
/**
 * Skrip CLI TypeScript Saluran Penghuraian PDF Warta Rasmi AGC (FASA 2 — Statute Ingestion Pipeline).
 *
 * Penggunaan:
 *   npx tsx scripts/ingest-statute.ts --file data/akta/AKTA_852.pdf --statute-id AKTA_852
 *   npx tsx scripts/ingest-statute.ts --audit
 */

import { spawnSync } from "node:child_process";
import path from "node:path";

const rootDir = path.resolve(__dirname, "..");
const pyScript = path.join(rootDir, "scripts", "ingest_statute.py");
const args = process.argv.slice(2);

const venvPython = path.join(rootDir, ".venv", "bin", "python");
const pythonBin = spawnSync(venvPython, ["--version"]).status === 0 ? venvPython : "python3";

const res = spawnSync(pythonBin, [pyScript, ...args], {
  cwd: rootDir,
  stdio: "inherit",
});

process.exit(res.status ?? 0);
