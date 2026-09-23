#!/usr/bin/env node
/**
 * Compare read-only endpoint access across anonymous and authorized profiles.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPlaywright } from "./playwright_runtime.mjs";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const SENSITIVE_PATH = /(admin|user|account|tenant|org|invite|material|audit|dashboard|profile|permission|role)/i;

function parseArgs(argv) {
  const args = { config: "", maxEndpoints: 100, timeout: 10000, url: "", workspace: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--config") {
      args.config = argv[++i];
    } else if (arg === "--url") {
      args.url = argv[++i];
    } else if (arg === "--workspace") {
      args.workspace = argv[++i];
    } else if (arg === "--max-endpoints") {
      args.maxEndpoints = Number(argv[++i]);
    } else if (arg === "--timeout") {
      args.timeout = Number(argv[++i]);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function usage() {
  const script = path.basename(fileURLToPath(import.meta.url));
  return `Usage: node ${script} --config <osr.config.json> --url <target-url> --workspace <audit-workspace> [--max-endpoints 100] [--timeout 10000]`;
}

async function readJson(filePath, fallback = {}) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

function resolvePath(baseDir, value) {
  if (!value) {
    return "";
  }
  return path.isAbsolute(value) ? value : path.resolve(baseDir, value);
}

function normalizeProfiles(config, configDir) {
  const access = config.accessMatrix || {};
  const configured = Array.isArray(access.profiles) ? access.profiles : [];
  const profiles = configured.length > 0 ? configured : [{ name: "anonymous" }];
  return profiles.map((profile, index) => {
    const headers = {};
    const headerEnv = profile.headersFromEnv || {};
    for (const [header, envName] of Object.entries(headerEnv)) {
      if (process.env[envName]) {
        headers[header] = process.env[envName];
      }
    }
    return {
      name: profile.name || `profile-${index + 1}`,
      storageState: resolvePath(configDir, profile.storageState || ""),
      headers,
      headerNames: Object.keys(headers),
      expectAccess: Boolean(profile.expectAccess),
      expectDenied: Boolean(profile.expectDenied),
    };
  });
}

function endpointKey(endpoint) {
  return `${endpoint.method || "GET"} ${endpoint.path}`;
}

function normalizeEndpoint(raw, origin, source) {
  const method = (raw.method || "GET").toUpperCase();
  const apiPath = raw.path || raw.url || "";
  if (!apiPath || !apiPath.startsWith("/")) {
    return null;
  }
  if (!SAFE_METHODS.has(method)) {
    return null;
  }
  return {
    method,
    path: apiPath,
    url: `${origin}${apiPath}`,
    kind: raw.kind || "endpoint",
    source,
  };
}

function endpointsFromPayload(payload, origin, source, includeUnknown = false) {
  const endpoints = [];
  for (const raw of payload.endpoints || []) {
    const method = (raw.method || "UNKNOWN").toUpperCase();
    const normalized = normalizeEndpoint({ ...raw, method: method === "UNKNOWN" && includeUnknown ? "GET" : method }, origin, source);
    if (normalized) {
      endpoints.push(normalized);
    }
  }
  return endpoints;
}

async function loadEndpoints(workspace, origin, config) {
  const state = path.join(workspace, "state");
  const apiMap = await readJson(path.join(state, "api_map.json"));
  const sourceMap = await readJson(path.join(state, "source_api_map.json"));
  const access = config.accessMatrix || {};
  const configuredPaths = Array.isArray(access.paths) ? access.paths : [];
  const endpointsByKey = new Map();

  for (const endpoint of endpointsFromPayload(apiMap, origin, "runtime")) {
    endpointsByKey.set(endpointKey(endpoint), endpoint);
  }
  const includeSourceOnly = access.includeSourceOnly !== false;
  if (includeSourceOnly) {
    for (const endpoint of endpointsFromPayload(sourceMap, origin, "source", Boolean(access.includeUnknownSourceAsGet))) {
      if (endpoint.kind === "base" && !access.includeBasePaths) {
        continue;
      }
      if (!endpointsByKey.has(endpointKey(endpoint))) {
        endpointsByKey.set(endpointKey(endpoint), endpoint);
      }
    }
  }
  for (const item of configuredPaths) {
    const endpoint = typeof item === "string" ? { method: "GET", path: item } : item;
    const normalized = normalizeEndpoint(endpoint, origin, "config");
    if (normalized) {
      endpointsByKey.set(endpointKey(normalized), normalized);
    }
  }

  return [...endpointsByKey.values()].slice(0, access.maxEndpoints || 100);
}

async function updateManifest(workspace) {
  const manifestPath = path.join(workspace, "state", "manifest.json");
  try {
    const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
    manifest.stages = manifest.stages || {};
    manifest.stages.role_matrix = "completed";
    await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  } catch {
    // Role matrix can run without a created workspace manifest.
  }
}

async function probeEndpoint(page, endpoint, profile, timeout) {
  try {
    return await page.evaluate(
      async ({ endpoint: browserEndpoint, profileHeaders, requestTimeout }) => {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), requestTimeout);
        try {
          const response = await fetch(browserEndpoint.url, {
            method: browserEndpoint.method,
            headers: profileHeaders,
            credentials: "include",
            cache: "no-store",
            redirect: "manual",
            signal: controller.signal,
          });
          const contentType = response.headers.get("content-type") || "";
          return {
            ok: true,
            status: response.status,
            finalUrl: response.url,
            contentType,
          };
        } finally {
          clearTimeout(timer);
        }
      },
      { endpoint, profileHeaders: profile.headers, requestTimeout: timeout },
    );
  } catch (error) {
    return { ok: false, status: null, error: error.message };
  }
}

function analyzeSignals(rows, profiles) {
  const signals = [];
  const rowsByEndpoint = new Map();
  for (const row of rows) {
    const key = endpointKey(row);
    const group = rowsByEndpoint.get(key) || [];
    group.push(row);
    rowsByEndpoint.set(key, group);
  }
  for (const [key, group] of rowsByEndpoint.entries()) {
    const anonymous = group.find((row) => row.profile === "anonymous");
    if (anonymous && anonymous.status !== null && anonymous.status < 400 && SENSITIVE_PATH.test(anonymous.path)) {
      signals.push({ severity: "medium", kind: "anonymous_sensitive_read_signal", endpoint: key, detail: "Anonymous profile received a successful response for a sensitive-looking path." });
    }
    const successStatuses = group.filter((row) => row.status !== null && row.status < 400).map((row) => row.profile);
    if (profiles.length > 1 && successStatuses.length === profiles.length && SENSITIVE_PATH.test(group[0].path)) {
      signals.push({ severity: "low", kind: "uniform_role_success_signal", endpoint: key, detail: "All configured profiles received successful responses for a sensitive-looking path; verify authorization logic." });
    }
    for (const row of group) {
      const profile = profiles.find((item) => item.name === row.profile);
      if (profile?.expectDenied && row.status !== null && row.status < 400) {
        signals.push({ severity: "high", kind: "unexpected_access_allowed", endpoint: key, detail: `${row.profile} was expected to be denied but received status ${row.status}.` });
      }
      if (profile?.expectAccess && (row.status === null || row.status >= 400)) {
        signals.push({ severity: "medium", kind: "expected_access_denied", endpoint: key, detail: `${row.profile} was expected to have access but received status ${row.status}.` });
      }
    }
  }
  return signals;
}

function renderMarkdown(payload) {
  const lines = [
    "# Role / Permission Matrix",
    "",
    `- Target: ${payload.targetUrl}`,
    `- Profiles: ${payload.profiles.map((profile) => profile.name).join(", ")}`,
    `- Endpoints tested: ${payload.endpoints.length}`,
    `- Requests sent: ${payload.rows.length}`,
    `- Signals: ${payload.signals.length}`,
    "",
    "## Signals",
  ];
  if (payload.signals.length === 0) {
    lines.push("- No role matrix signals found.");
  }
  for (const signal of payload.signals) {
    lines.push(`- ${signal.severity}: ${signal.kind} - ${signal.endpoint} - ${signal.detail}`);
  }
  lines.push("", "## Matrix");
  for (const endpoint of payload.endpoints) {
    lines.push(`### ${endpoint.method} ${endpoint.path}`);
    for (const row of payload.rows.filter((item) => item.method === endpoint.method && item.path === endpoint.path)) {
      lines.push(`- ${row.profile}: status=${row.status ?? ""} ok=${row.ok} source=${row.source}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }
  if (!args.config || !args.url || !args.workspace) {
    throw new Error(usage());
  }

  const configPath = path.resolve(args.config);
  const configDir = path.dirname(configPath);
  const config = JSON.parse(await fs.readFile(configPath, "utf8"));
  const workspace = path.resolve(args.workspace);
  const origin = new URL(args.url).origin;
  const profiles = normalizeProfiles(config, configDir);
  const endpoints = (await loadEndpoints(workspace, origin, config)).slice(0, args.maxEndpoints);

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const rows = [];
  try {
    for (const profile of profiles) {
      const contextOptions = {};
      if (profile.storageState) {
        contextOptions.storageState = profile.storageState;
      }
      const context = await browser.newContext(contextOptions);
      const page = await context.newPage();
      try {
        await page.goto(origin, { waitUntil: "domcontentloaded", timeout: args.timeout });
      } catch {
        // API fetches may still work even if the landing page fails.
      }
      for (const endpoint of endpoints) {
        const result = await probeEndpoint(page, endpoint, profile, args.timeout);
        rows.push({
          profile: profile.name,
          method: endpoint.method,
          path: endpoint.path,
          url: endpoint.url,
          source: endpoint.source,
          kind: endpoint.kind,
          ok: result.ok,
          status: result.status,
          error: result.error || "",
          contentType: result.contentType || "",
          headerNames: profile.headerNames,
        });
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }

  const payload = {
    generatedFrom: "role_matrix",
    targetUrl: args.url,
    profiles: profiles.map((profile) => ({ name: profile.name, storageState: Boolean(profile.storageState), headerNames: profile.headerNames })),
    endpoints,
    rows,
    signals: analyzeSignals(rows, profiles),
  };

  const stateDir = path.join(workspace, "state");
  const evidenceDir = path.join(workspace, "evidence");
  await fs.mkdir(stateDir, { recursive: true });
  await fs.mkdir(evidenceDir, { recursive: true });
  await fs.writeFile(path.join(stateDir, "role_matrix.json"), `${JSON.stringify(payload, null, 2)}\n`);
  await fs.writeFile(path.join(evidenceDir, "role_matrix.md"), renderMarkdown(payload));
  await updateManifest(workspace);

  console.log(JSON.stringify({ endpoints: endpoints.length, requests: rows.length, signals: payload.signals.length, json: path.join(stateDir, "role_matrix.json") }));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
