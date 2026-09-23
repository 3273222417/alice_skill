#!/usr/bin/env node
/**
 * Passive Playwright crawl for local or explicitly authorized web apps.
 *
 * The crawler visits same-origin links, records response metadata, and blocks
 * non-read HTTP methods to avoid accidental mutations.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadPlaywright } from "./playwright_runtime.mjs";

function parseArgs(argv) {
  const args = { maxPages: 20, storageState: "", timeout: 10000, workspace: "", url: "" };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--url") {
      args.url = argv[++i];
    } else if (arg === "--workspace") {
      args.workspace = argv[++i];
    } else if (arg === "--max-pages") {
      args.maxPages = Number(argv[++i]);
    } else if (arg === "--timeout") {
      args.timeout = Number(argv[++i]);
    } else if (arg === "--storage-state") {
      args.storageState = argv[++i];
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function usage() {
  const script = path.basename(fileURLToPath(import.meta.url));
  return `Usage: node ${script} --url <target-url> --workspace <audit-workspace> [--max-pages 20] [--timeout 10000] [--storage-state state/authenticated-storage-state.json]`;
}

function sameOrigin(url, origin) {
  try {
    const parsed = new URL(url);
    return parsed.origin === origin && ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}

function requestPath(url) {
  try {
    const parsed = new URL(url);
    return parsed.pathname;
  } catch {
    return "";
  }
}

function buildApiMap(result) {
  const responsesById = new Map(result.responses.map((item) => [item.requestId, item]));
  const grouped = new Map();
  for (const request of result.requests) {
    const parsed = new URL(request.url);
    const same = parsed.origin === result.origin;
    const pathName = parsed.pathname;
    const apiLike = same && (
      request.resourceType === "fetch" ||
      request.resourceType === "xhr" ||
      pathName.startsWith("/api") ||
      pathName.includes("/api/")
    );
    if (!apiLike) {
      continue;
    }
    const key = `${request.method} ${parsed.origin}${pathName}`;
    const response = responsesById.get(request.id);
    const existing = grouped.get(key) || {
      method: request.method,
      origin: parsed.origin,
      path: pathName,
      sameOrigin: same,
      resourceTypes: {},
      statuses: {},
      count: 0,
      firstSeenFromPage: request.pageUrl,
      examples: [],
    };
    existing.count += 1;
    existing.resourceTypes[request.resourceType] = (existing.resourceTypes[request.resourceType] || 0) + 1;
    const status = response ? String(response.status) : "pending_or_failed";
    existing.statuses[status] = (existing.statuses[status] || 0) + 1;
    if (existing.examples.length < 5) {
      existing.examples.push({
        url: request.url,
        pageUrl: request.pageUrl,
        status: response ? response.status : null,
        queryPresent: parsed.search.length > 0,
      });
    }
    grouped.set(key, existing);
  }
  return {
    generatedFrom: "passive_crawl",
    endpointCount: grouped.size,
    endpoints: [...grouped.values()].sort((a, b) => `${a.method} ${a.path}`.localeCompare(`${b.method} ${b.path}`)),
  };
}

function renderApiMap(apiMap) {
  const lines = [
    "# API / Request Map",
    "",
    `- Endpoints observed: ${apiMap.endpointCount}`,
    "",
  ];
  for (const endpoint of apiMap.endpoints) {
    lines.push(`## ${endpoint.method} ${endpoint.path}`);
    lines.push("");
    lines.push(`- Origin: ${endpoint.origin}`);
    lines.push(`- Count: ${endpoint.count}`);
    lines.push(`- Resource types: ${Object.entries(endpoint.resourceTypes).map(([key, value]) => `${key}=${value}`).join(", ")}`);
    lines.push(`- Statuses: ${Object.entries(endpoint.statuses).map(([key, value]) => `${key}=${value}`).join(", ")}`);
    lines.push(`- First seen from: ${endpoint.firstSeenFromPage || "unknown"}`);
    lines.push("- Examples:");
    for (const example of endpoint.examples) {
      lines.push(`  - \`${example.url}\` status=${example.status ?? ""} query=${example.queryPresent}`);
    }
    lines.push("");
  }
  return lines.join("\n");
}

async function updateManifest(workspace) {
  const manifestPath = path.join(workspace, "state", "manifest.json");
  try {
    const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
    manifest.stages = manifest.stages || {};
    manifest.stages.passive_crawl = "completed";
    await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  } catch {
    // Workspace may not have a manifest; crawling still succeeds.
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }
  if (!args.url || !args.workspace) {
    throw new Error(usage());
  }

  const { chromium } = loadPlaywright();
  const start = new URL(args.url);
  const origin = start.origin;
  const workspace = path.resolve(args.workspace);
  const stateDir = path.join(workspace, "state");
  const evidenceDir = path.join(workspace, "evidence");
  await fs.mkdir(stateDir, { recursive: true });
  await fs.mkdir(evidenceDir, { recursive: true });

  const result = {
    startUrl: args.url,
    origin,
    pages: [],
    requests: [],
    responses: [],
    requestFailures: [],
    blockedRequests: [],
    console: [],
  };
  const requestIds = new WeakMap();
  let requestCounter = 0;

  const browser = await chromium.launch({ headless: true });
  const contextOptions = {};
  if (args.storageState) {
    contextOptions.storageState = path.resolve(args.storageState);
  }
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  await page.route("**/*", async (route) => {
    const request = route.request();
    const method = request.method().toUpperCase();
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      result.blockedRequests.push({ method, url: request.url() });
      await route.abort();
      return;
    }
    await route.continue();
  });

  page.on("request", (request) => {
    const id = `req-${++requestCounter}`;
    requestIds.set(request, id);
    result.requests.push({
      id,
      method: request.method(),
      url: request.url(),
      path: requestPath(request.url()),
      resourceType: request.resourceType(),
      pageUrl: page.url(),
    });
  });
  page.on("response", (response) => {
    const request = response.request();
    result.responses.push({
      requestId: requestIds.get(request) || null,
      url: response.url(),
      path: requestPath(response.url()),
      status: response.status(),
    });
  });
  page.on("requestfailed", (request) => {
    result.requestFailures.push({
      requestId: requestIds.get(request) || null,
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "",
    });
  });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      result.console.push({ type: message.type(), text: message.text() });
    }
  });

  const queue = [args.url];
  const seen = new Set();
  while (queue.length > 0 && result.pages.length < args.maxPages) {
    const current = queue.shift();
    if (!current || seen.has(current) || !sameOrigin(current, origin)) {
      continue;
    }
    seen.add(current);
    let pageInfo = { url: current, status: null, title: "", links: [] };
    try {
      const response = await page.goto(current, { waitUntil: "domcontentloaded", timeout: args.timeout });
      pageInfo.status = response ? response.status() : null;
      pageInfo.title = await page.title();
      const links = await page.$$eval("a[href]", (anchors) => anchors.map((anchor) => anchor.href));
      pageInfo.links = [...new Set(links.filter((link) => {
        try {
          const parsed = new URL(link);
          return parsed.origin === location.origin && ["http:", "https:"].includes(parsed.protocol);
        } catch {
          return false;
        }
      }))].slice(0, 100);
      for (const link of pageInfo.links) {
        if (!seen.has(link) && queue.length + result.pages.length < args.maxPages * 2) {
          queue.push(link);
        }
      }
    } catch (error) {
      pageInfo.error = error.message;
    }
    result.pages.push(pageInfo);
  }

  await context.close();
  await browser.close();

  const jsonPath = path.join(stateDir, "passive_crawl.json");
  const apiMap = buildApiMap(result);
  const apiMapPath = path.join(stateDir, "api_map.json");
  const mdPath = path.join(evidenceDir, "passive_crawl.md");
  const apiMapMdPath = path.join(evidenceDir, "api_map.md");
  await fs.writeFile(jsonPath, `${JSON.stringify(result, null, 2)}\n`);
  await fs.writeFile(apiMapPath, `${JSON.stringify(apiMap, null, 2)}\n`);
  const lines = [
    "# Passive Crawl",
    "",
    `- Start URL: ${result.startUrl}`,
    `- Pages visited: ${result.pages.length}`,
    `- Requests observed: ${result.requests.length}`,
    `- Non-read requests blocked: ${result.blockedRequests.length}`,
    `- Authenticated storage state: ${args.storageState ? "yes" : "no"}`,
    "",
    "## Pages",
    ...result.pages.map((item) => `- \`${item.url}\` status=${item.status ?? ""} title=${JSON.stringify(item.title || "")}`),
    "",
  ];
  await fs.writeFile(mdPath, lines.join("\n"));
  await fs.writeFile(apiMapMdPath, renderApiMap(apiMap));
  await updateManifest(workspace);
  console.log(JSON.stringify({ apiMap: apiMapPath, json: jsonPath, markdown: mdPath, pages: result.pages.length }));
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
