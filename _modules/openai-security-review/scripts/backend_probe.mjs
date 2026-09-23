#!/usr/bin/env node
/**
 * Read-only backend runtime validation for same-origin endpoints.
 */

import fs from "node:fs/promises";
import path from "node:path";

function parseArgs(argv) {
  const args = { paths: "", maxEndpoints: 50, timeout: 10000, storageState: "", config: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--url") args.url = argv[++i];
    else if (arg === "--workspace") args.workspace = argv[++i];
    else if (arg === "--config") args.config = argv[++i];
    else if (arg === "--paths") args.paths = argv[++i];
    else if (arg === "--max-endpoints") args.maxEndpoints = Number(argv[++i]);
    else if (arg === "--timeout") args.timeout = Number(argv[++i]);
    else if (arg === "--storage-state") args.storageState = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!args.url || !args.workspace) {
    throw new Error("Usage: node scripts/backend_probe.mjs --url <url> --workspace <workspace> [--config osr.config.json]");
  }
  return args;
}

async function readJson(filePath, fallback = {}) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

async function writeJson(filePath, payload) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function dynamicPath(value) {
  return /[:*{}\[\]()]|\.\.\./.test(value);
}

function normalizeCandidate(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) return null;
  const methodMatch = /^(GET|HEAD|OPTIONS)\s+(.+)$/i.exec(trimmed);
  if (methodMatch) {
    return { method: methodMatch[1].toUpperCase(), path: methodMatch[2].trim(), source: "config" };
  }
  return { method: "GET", path: trimmed, source: "config" };
}

function sameOriginUrl(baseUrl, routePath) {
  const base = new URL(baseUrl);
  const target = new URL(routePath, base);
  if (target.origin !== base.origin) return null;
  return target;
}

async function cookieHeader(storageStatePath, targetUrl) {
  if (!storageStatePath) return "";
  const state = await readJson(storageStatePath, {});
  const cookies = Array.isArray(state.cookies) ? state.cookies : [];
  const target = new URL(targetUrl);
  const pairs = [];
  for (const cookie of cookies) {
    const domain = String(cookie.domain || "").replace(/^\./, "");
    if (domain && target.hostname !== domain && !target.hostname.endsWith(`.${domain}`)) continue;
    if (cookie.path && !target.pathname.startsWith(cookie.path)) continue;
    pairs.push(`${cookie.name}=${cookie.value}`);
  }
  return pairs.join("; ");
}

function candidatesFromRouteMap(routeMap) {
  const candidates = [];
  for (const route of routeMap.routes || []) {
    const method = String(route.method || "UNKNOWN").toUpperCase();
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) continue;
    const routePath = route.path || "";
    if (!routePath || dynamicPath(routePath)) continue;
    candidates.push({ method, path: routePath, source: "server_route_map" });
  }
  return candidates;
}

function uniqueCandidates(items, limit) {
  const seen = new Set();
  const output = [];
  for (const item of items) {
    const key = `${item.method} ${item.path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    output.push(item);
    if (output.length >= limit) break;
  }
  return output;
}

async function requestWithTimeout(url, options, timeout) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(url, { ...options, signal: controller.signal, redirect: "manual" });
  } finally {
    clearTimeout(timer);
  }
}

async function probe(baseUrl, candidate, args, cookie) {
  const target = sameOriginUrl(baseUrl, candidate.path);
  if (!target) {
    return { ...candidate, skipped: true, reason: "cross_origin" };
  }
  const headers = { Accept: "application/json,text/plain,*/*" };
  if (cookie) headers.Cookie = cookie;
  const started = Date.now();
  try {
    const response = await requestWithTimeout(target.toString(), { method: candidate.method, headers }, args.timeout);
    const contentType = response.headers.get("content-type") || "";
    let sample = "";
    if (candidate.method === "GET" && /json|text|html|xml|yaml|plain/i.test(contentType)) {
      sample = (await response.text()).slice(0, 4096);
    }
    const signals = [];
    if (/swagger|openapi/i.test(target.pathname) && response.status < 400) {
      signals.push({ severity: "info", kind: "api_spec_exposed", detail: `${target.pathname} is reachable.` });
    }
    if (/Traceback|stack trace|Exception|TypeError|ReferenceError|SQL syntax|at\s+\S+\s+\(/i.test(sample)) {
      signals.push({ severity: "medium", kind: "error_detail_exposure", detail: "Response sample contains stack-trace or exception-like text." });
    }
    return {
      ...candidate,
      url: target.toString(),
      status: response.status,
      ok: response.ok,
      durationMs: Date.now() - started,
      contentType,
      location: response.headers.get("location") || "",
      signals,
    };
  } catch (error) {
    return { ...candidate, url: target.toString(), error: error.message, durationMs: Date.now() - started, signals: [] };
  }
}

async function updateManifest(workspace) {
  const manifestPath = path.join(workspace, "state", "manifest.json");
  const manifest = await readJson(manifestPath, {});
  if (!Object.keys(manifest).length) return;
  manifest.stages = manifest.stages || {};
  manifest.stages.backend_runtime_validation = "completed";
  await writeJson(manifestPath, manifest);
}

function renderMarkdown(payload) {
  const lines = [
    "# Backend Runtime Validation",
    "",
    `- Target: \`${payload.targetUrl}\``,
    `- Candidates: ${payload.candidates}`,
    `- Requests sent: ${payload.results.length}`,
    `- Signals: ${payload.signals.length}`,
    "",
    "## Results",
  ];
  if (!payload.results.length) lines.push("- No endpoints probed.");
  for (const result of payload.results.slice(0, 100)) {
    if (result.skipped) {
      lines.push(`- skipped \`${result.method} ${result.path}\` ${result.reason}`);
    } else if (result.error) {
      lines.push(`- error \`${result.method} ${result.path}\` ${result.error}`);
    } else {
      lines.push(`- ${result.status} \`${result.method} ${result.path}\` ${result.contentType || ""}`);
    }
  }
  if (payload.signals.length) {
    lines.push("", "## Signals");
    for (const signal of payload.signals.slice(0, 50)) {
      lines.push(`- ${signal.severity}: ${signal.kind} - ${signal.endpoint} - ${signal.detail}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const workspace = path.resolve(args.workspace);
  const stateDir = path.join(workspace, "state");
  const evidenceDir = path.join(workspace, "evidence");
  await fs.mkdir(stateDir, { recursive: true });
  await fs.mkdir(evidenceDir, { recursive: true });

  const config = args.config ? await readJson(args.config, {}) : {};
  const backend = config.backend || {};
  const configured = [
    ...(Array.isArray(backend.runtimeProbePaths) ? backend.runtimeProbePaths : []),
    ...args.paths.split(",").map((item) => item.trim()).filter(Boolean),
  ].map(normalizeCandidate).filter(Boolean);
  const routeMap = await readJson(path.join(stateDir, "server_route_map.json"), {});
  const common = ["/health", "/api/health", "/version", "/api/version", "/openapi.json", "/swagger.json"].map((item) => ({ method: "GET", path: item, source: "common" }));
  const candidates = uniqueCandidates([...configured, ...candidatesFromRouteMap(routeMap), ...common], args.maxEndpoints);
  const cookie = await cookieHeader(args.storageState || backend.storageState || "", args.url);
  const results = [];
  for (const candidate of candidates) {
    results.push(await probe(args.url, candidate, args, cookie));
  }
  const signals = results.flatMap((result) => (result.signals || []).map((signal) => ({ ...signal, endpoint: `${result.method} ${result.path}` })));
  const payload = {
    generatedFrom: "backend_probe",
    targetUrl: args.url,
    candidates: candidates.length,
    results,
    signals,
    guardrail: "same-origin GET/HEAD/OPTIONS requests only; no request bodies are sent.",
  };
  await writeJson(path.join(stateDir, "backend_runtime_validation.json"), payload);
  await fs.writeFile(path.join(evidenceDir, "backend_runtime_validation.md"), renderMarkdown(payload), "utf8");
  await updateManifest(workspace);
  console.log(JSON.stringify({ candidates: candidates.length, requests: results.length, signals: signals.length }));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
