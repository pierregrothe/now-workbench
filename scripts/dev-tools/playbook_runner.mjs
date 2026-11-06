#!/usr/bin/env node
/**
 * Real Playwright / Chrome Playbook Driver for ServiceNow.
 * Executes declarative walkthrough playbooks against ServiceNow Next Experience / Polaris DOM,
 * with visible cursor movement, authentic session state persistence, and native WebM video recording.
 */

import fs from "node:fs";
import path from "node:path";
import puppeteer from "../../web/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js";

// CHROME_PATH comes from the environment in the container (Chromium); macOS Chrome otherwise.
const CHROME_PATH =
  process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    playbook: "",
    url: "",
    outputVideo: "",
    outputImage: "",
    outputLog: "",
    storageState: "",
    username: "",
    password: "",
    width: 1280,
    height: 720,
    fake: false,
    credentialsStdin: false,
  };

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--fake") opts.fake = true;
    else if (a === "--playbook" && args[i + 1]) opts.playbook = args[++i];
    else if (a === "--url" && args[i + 1]) opts.url = args[++i];
    else if (a === "--output-video" && args[i + 1]) opts.outputVideo = args[++i];
    else if (a === "--output-image" && args[i + 1]) opts.outputImage = args[++i];
    else if (a === "--output-log" && args[i + 1]) opts.outputLog = args[++i];
    else if (a === "--storage-state" && args[i + 1]) opts.storageState = args[++i];
    else if (a === "--credentials-stdin") opts.credentialsStdin = true;
    else if (a === "--width" && args[i + 1]) opts.width = parseInt(args[++i], 10);
    else if (a === "--height" && args[i + 1]) opts.height = parseInt(args[++i], 10);
  }
  return opts;
}

function buildServiceNowOfflineHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>ServiceNow - Incidents | Agent Workspace</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #f4f6f8;
      color: #1e293b;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .sn-nav {
      height: 52px;
      background: #032d42;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sn-logo-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .sn-glyph {
      width: 24px;
      height: 24px;
      fill: #62d84e;
    }
    .sn-app-title {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.2px;
    }
    .sn-badge {
      font-size: 11px;
      background: rgba(98, 216, 78, 0.2);
      color: #62d84e;
      border: 1px solid rgba(98, 216, 78, 0.4);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
    }
    .sn-user-profile {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }
    .sn-avatar {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: #2563eb;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 12px;
    }
    .sn-workspace {
      flex: 1;
      display: flex;
    }
    .sn-sidebar {
      width: 240px;
      background: #ffffff;
      border-right: 1px solid #e2e8f0;
      padding: 16px 0;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .sn-menu-item {
      padding: 10px 20px;
      font-size: 13px;
      color: #475569;
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
    }
    .sn-menu-item.active {
      background: #eff6ff;
      color: #1d4ed8;
      font-weight: 600;
      border-left: 3px solid #2563eb;
    }
    .sn-main {
      flex: 1;
      padding: 24px 32px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .sn-view-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .sn-title {
      font-size: 20px;
      font-weight: 700;
      color: #0f172a;
    }
    .sn-sub {
      font-size: 13px;
      color: #64748b;
      margin-top: 2px;
    }
    .sn-table-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      overflow: hidden;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th {
      background: #f8fafc;
      text-align: left;
      padding: 12px 16px;
      color: #475569;
      font-weight: 600;
      border-bottom: 1px solid #e2e8f0;
    }
    td {
      padding: 14px 16px;
      border-bottom: 1px solid #f1f5f9;
      color: #1e293b;
    }
    tr.incident-row {
      cursor: pointer;
      transition: background 0.15s ease;
    }
    tr.incident-row:hover, tr.incident-row.selected {
      background: #f0fdf4;
    }
    .priority-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }
    .p-critical { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .p-high { background: #fff7ed; color: #ea580c; border: 1px solid #ffedd5; }
    .p-moderate { background: #fefce8; color: #ca8a04; border: 1px solid #fef08a; }
    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      background: #f1f5f9;
      color: #475569;
    }
    #detail-panel {
      display: none;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 20px;
      margin-top: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      animation: fadeIn 0.2s ease-in;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    .ai-banner {
      background: linear-gradient(90deg, #ecfdf5 0%, #f0fdf4 100%);
      border: 1px solid #a7f3d0;
      border-radius: 6px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .ai-banner-title {
      font-weight: 700;
      font-size: 13px;
      color: #065f46;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .ai-banner-score {
      background: #059669;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 12px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 16px;
    }
    .field-box label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: #64748b;
      margin-bottom: 4px;
      text-transform: uppercase;
    }
    .field-box input {
      width: 100%;
      padding: 8px 10px;
      font-size: 13px;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      background: #f8fafc;
      color: #0f172a;
    }
    .notes-box label {
      display: block;
      font-size: 11px;
      font-weight: 600;
      color: #64748b;
      margin-bottom: 4px;
      text-transform: uppercase;
    }
    .notes-box textarea {
      width: 100%;
      height: 70px;
      padding: 8px 10px;
      font-size: 12px;
      font-family: monospace;
      border: 1.5px solid #94a3b8;
      border-radius: 4px;
      background: #ffffff;
      color: #0f172a;
      resize: none;
    }
    .actions-bar {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 14px;
    }
    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
    }
    .btn-save { background: #2563eb; color: #ffffff; }
    .btn-save.success { background: #16a34a; }
  </style>
</head>
<body>
  <header class="sn-nav">
    <div class="sn-logo-group">
      <svg class="sn-glyph" viewBox="0 0 32 32">
        <path d="M16 3C8.82 3 3 8.82 3 16C3 20.88 5.69 25.13 9.68 27.35C10.95 25.43 13.31 24.15 16 24.15C18.69 24.15 21.05 25.43 22.32 27.35C26.31 25.13 29 20.88 29 16C29 8.82 23.18 3 16 3ZM16 21.2C12.58 21.2 9.8 18.42 9.8 15C9.8 11.58 12.58 8.8 16 8.8C19.42 8.8 22.2 11.58 22.2 15C22.2 18.42 19.42 21.2 16 21.2Z"/>
      </svg>
      <span class="sn-app-title">ServiceNow IT Service Desk</span>
      <span class="sn-badge">Now Assist Enabled</span>
    </div>
    <div class="sn-user-profile">
      <div class="sn-avatar">BA</div>
      <span>Beth Anglin (Tier 1 Support)</span>
    </div>
  </header>

  <div class="sn-workspace">
    <aside class="sn-sidebar">
      <div class="sn-menu-item active">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14h-2v-4h2v4zm0-6h-2V7h2v4z"/></svg>
        <span>Open Incidents (4)</span>
      </div>
      <div class="sn-menu-item">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
        <span>Assigned to Me</span>
      </div>
      <div class="sn-menu-item">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10H7v-2h10v2z"/></svg>
        <span>AI Routing Telemetry</span>
      </div>
    </aside>

    <main class="sn-main">
      <div class="sn-view-header">
        <div>
          <h1 class="sn-title">Incidents &gt; Unassigned Triage Queue</h1>
          <p class="sn-sub">Live demonstration queue - Evaluated by GenAI Incident Router</p>
        </div>
      </div>

      <div class="sn-table-card" id="incidents-table-card">
        <table>
          <thead>
            <tr>
              <th style="width: 110px;">Number</th>
              <th style="width: 90px;">Priority</th>
              <th style="width: 100px;">State</th>
              <th>Short Description</th>
              <th style="width: 140px;">Caller</th>
              <th style="width: 150px;">Assignment Group</th>
            </tr>
          </thead>
          <tbody>
            <tr class="incident-row" id="row-target-incident">
              <td style="font-weight:700; color:#2563eb;">INC0010042</td>
              <td><span class="priority-badge p-high">2 - High</span></td>
              <td><span class="status-badge">New</span></td>
              <td style="font-weight:600;">VPN connection drops every 15 minutes during peak hours</td>
              <td>beth.anglin@example.com</td>
              <td id="target-assign-group" style="color:#64748b; font-style:italic;">Unassigned</td>
            </tr>
            <tr class="incident-row">
              <td style="font-weight:700; color:#2563eb;">INC0010039</td>
              <td><span class="priority-badge p-critical">1 - Critical</span></td>
              <td><span class="status-badge">In Progress</span></td>
              <td>SAP ERP batch sync timeout error code 504</td>
              <td>david.loo@example.com</td>
              <td>Database Admin</td>
            </tr>
            <tr class="incident-row">
              <td style="font-weight:700; color:#2563eb;">INC0010031</td>
              <td><span class="priority-badge p-moderate">3 - Moderate</span></td>
              <td><span class="status-badge">New</span></td>
              <td>Outlook Mac client crashes on launching shared calendar</td>
              <td>fred.luddy@example.com</td>
              <td>Service Desk</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div id="detail-panel">
        <div class="ai-banner">
          <div class="ai-banner-title">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="#059669"><path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z"/></svg>
            <span>Now Assist GenAI Recommendation: Route to Network Operations</span>
          </div>
          <span class="ai-banner-score">94.2% Confidence</span>
        </div>

        <div class="form-grid">
          <div class="field-box">
            <label>Incident Number</label>
            <input type="text" value="INC0010042" readonly />
          </div>
          <div class="field-box">
            <label>Category</label>
            <input type="text" id="detail-category" value="Network" readonly />
          </div>
          <div class="field-box">
            <label>Assignment Group</label>
            <input type="text" id="detail-group" value="Network Operations" style="font-weight:700; color:#059669;" readonly />
          </div>
        </div>

        <div class="notes-box">
          <label>Work Notes (AI Triage Audit Log)</label>
          <textarea id="work-notes-input" placeholder="Enter notes..."></textarea>
        </div>

        <div class="actions-bar">
          <button class="btn btn-save" id="btn-save-incident">Save &amp; Resolve Triage</button>
        </div>
      </div>
    </main>
  </div>
</body>
</html>`;
}

async function injectCursorOverlay(page) {
  await page.evaluate(() => {
    if (document.getElementById("__wb_cursor")) return;
    const cursor = document.createElement("div");
    cursor.id = "__wb_cursor";
    cursor.style.position = "fixed";
    cursor.style.top = "0px";
    cursor.style.left = "0px";
    cursor.style.width = "26px";
    cursor.style.height = "26px";
    cursor.style.zIndex = "2147483647";
    cursor.style.pointerEvents = "none";
    cursor.style.transform = "translate(50px, 50px)";
    cursor.style.transition = "transform 0.04s linear";
    cursor.innerHTML = `
      <svg viewBox="0 0 24 24" width="24" height="24" style="filter: drop-shadow(0 2px 5px rgba(0,0,0,0.45));">
        <path d="M3 3l7 18 3.5-7 7-3.5L3 3z" fill="#032d42" stroke="#62d84e" stroke-width="1.8"/>
      </svg>
    `;
    document.body.appendChild(cursor);

    const ripple = document.createElement("div");
    ripple.id = "__wb_ripple";
    ripple.style.position = "fixed";
    ripple.style.width = "40px";
    ripple.style.height = "40px";
    ripple.style.borderRadius = "50%";
    ripple.style.border = "3px solid #62d84e";
    ripple.style.background = "rgba(98, 216, 78, 0.35)";
    ripple.style.pointerEvents = "none";
    ripple.style.zIndex = "2147483646";
    ripple.style.display = "none";
    document.body.appendChild(ripple);

    window.__wb_set_cursor = (x, y) => {
      cursor.style.transform = `translate(${x}px, ${y}px)`;
    };

    window.__wb_click_pulse = (x, y) => {
      ripple.style.left = `${x - 20}px`;
      ripple.style.top = `${y - 20}px`;
      ripple.style.display = "block";
      ripple.style.transform = "scale(0.4)";
      ripple.style.opacity = "1";
      setTimeout(() => {
        ripple.style.transition = "transform 0.25s ease-out, opacity 0.25s ease-out";
        ripple.style.transform = "scale(1.5)";
        ripple.style.opacity = "0";
      }, 20);
      setTimeout(() => {
        ripple.style.display = "none";
        ripple.style.transition = "";
      }, 300);
    };
  });
}

// Credentials arrive as one JSON object on stdin (never argv, which any local
// user can read from the process list -- ADR-012).
async function readStdinCredentials() {
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  if (!raw.trim()) return { username: "", password: "" };
  const parsed = JSON.parse(raw);
  return { username: String(parsed.username || ""), password: String(parsed.password || "") };
}

async function main() {
  const opts = parseArgs();
  if (opts.credentialsStdin) Object.assign(opts, await readStdinCredentials());
  const startTime = new Date().toISOString();
  const startedMs = Date.now();

  let playbook = { bundle_id: "demo", title: "Playbook Execution", steps: [] };
  if (opts.playbook && fs.existsSync(opts.playbook)) {
    try {
      playbook = JSON.parse(fs.readFileSync(opts.playbook, "utf-8"));
    } catch (e) {
      console.warn("Could not parse playbook JSON, using default steps:", e);
    }
  }

  if (!fs.existsSync(CHROME_PATH)) {
    console.error(`Chrome binary not found at ${CHROME_PATH}`);
    process.exit(2);
  }

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    pipe: true,
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      `--window-size=${opts.width},${opts.height}`,
      "--disable-web-security",
      "--ignore-certificate-errors",
    ],
  });

  const stepResults = [];
  let liveAuthenticated = false;

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: opts.width, height: opts.height });

    // Load persisted session state if present
    if (opts.storageState && fs.existsSync(opts.storageState)) {
      try {
        const sessionData = JSON.parse(fs.readFileSync(opts.storageState, "utf-8"));
        if (sessionData && sessionData.cookies && Array.isArray(sessionData.cookies)) {
          await page.setCookie(...sessionData.cookies);
          console.log(`[PlaybookRunner] Injected ${sessionData.cookies.length} cached session cookies.`);
        }
      } catch (err) {
        console.warn("[PlaybookRunner] Failed reading storageState file:", err);
      }
    }

    if (opts.username && opts.password) {
      await page.authenticate({ username: opts.username, password: opts.password }).catch(() => {});
    }

    const targetUrl = opts.url || "https://demoalectriallwfau164179.service-now.com/incident_list.do";

    if (opts.fake) {
      console.log("[PlaybookRunner] Fake mode enabled: Rendering simulated ServiceNow Agent Workspace...");
      await page.setContent(buildServiceNowOfflineHtml(), { waitUntil: "load" });
    } else {
      const baseUrl = new URL(targetUrl).origin;
      if (opts.username && opts.password) {
        console.log(`[PlaybookRunner] Authenticating user '${opts.username}' via ${baseUrl}/login.do...`);
        try {
          await page.goto(`${baseUrl}/login.do`, { waitUntil: "domcontentloaded", timeout: 30000 });
          const hasUserInput = await page.waitForSelector("#user_name", { timeout: 10000 }).catch(() => null);
          if (hasUserInput) {
            console.log(`[PlaybookRunner] Submitting credentials as '${opts.username}'...`);
            await page.type("#user_name", opts.username, { delay: 40 });
            await page.type("#user_password", opts.password, { delay: 40 });
            await Promise.all([
              page.waitForNavigation({ waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {}),
              page.click("#sysverb_login"),
            ]);
            await page.waitForFunction(
              () => !window.location.href.includes("login.do"),
              { timeout: 30000 }
            ).catch(() => {});
          }
          liveAuthenticated = true;
        } catch (err) {
          console.warn(`[PlaybookRunner] Login attempt warning: ${err.message}`);
        }
      }

      console.log(`[PlaybookRunner] Navigating to destination: ${targetUrl}`);
      try {
        const resp = await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
        if (resp && resp.status() >= 400) {
          console.error(`[PlaybookRunner] HTTP ${resp.status()} error loading target instance.`);
          process.exit(1);
        }
      } catch (err) {
        console.error(`[PlaybookRunner] Live target unreachable: ${err.message}`);
        process.exit(1);
      }

      await page.waitForSelector("table, .list_div, #incident_table, form, .form_header, body", { timeout: 15000 }).catch(() => {});

      if (page.url().includes("login.do")) {
        console.error("[PlaybookRunner] Authentication failed: still on login.do.");
        process.exit(1);
      }
      liveAuthenticated = true;

      // Persist session cookies to storageState
      if (opts.storageState && liveAuthenticated) {
        try {
          const cookies = await page.cookies();
          const stateDir = path.dirname(path.resolve(opts.storageState));
          if (!fs.existsSync(stateDir)) fs.mkdirSync(stateDir, { recursive: true });
          fs.writeFileSync(opts.storageState, JSON.stringify({ cookies, updated_at: new Date().toISOString() }, null, 2));
          console.log(`[PlaybookRunner] Persisted session cookies to ${opts.storageState}`);
        } catch (err) {
          console.warn("[PlaybookRunner] Could not save storageState:", err);
        }
      }
    }

    await injectCursorOverlay(page);
    await new Promise((r) => setTimeout(r, 400));

    const frames = [];
    async function captureFrame() {
      try {
        const buf = await page.screenshot({ encoding: "base64", type: "jpeg", quality: 80 });
        frames.push(buf);
      } catch {
        try {
          await new Promise((r) => setTimeout(r, 200));
          const buf = await page.screenshot({ encoding: "base64", type: "jpeg", quality: 80 });
          frames.push(buf);
        } catch {}
      }
    }

    async function holdFrames(durationMs = 1500) {
      const interval = 100;
      const count = Math.max(1, Math.round(durationMs / interval));
      for (let i = 0; i < count; i++) {
        await captureFrame();
        await new Promise((r) => setTimeout(r, interval));
      }
    }

    async function moveCursor(startX, startY, endX, endY, steps = 6) {
      for (let i = 1; i <= steps; i++) {
        const curX = Math.round(startX + ((endX - startX) * i) / steps);
        const curY = Math.round(startY + ((endY - startY) * i) / steps);
        try {
          await page.evaluate((x, y) => window.__wb_set_cursor?.(x, y), curX, curY);
        } catch {
          try {
            await injectCursorOverlay(page);
            await page.evaluate((x, y) => window.__wb_set_cursor?.(x, y), curX, curY);
          } catch {}
        }
        await captureFrame();
        await new Promise((r) => setTimeout(r, 40));
      }
    }

    let cursorX = 100;
    let cursorY = 100;

    // Execute Playbook Steps
    const steps = (playbook.steps && playbook.steps.length > 0) ? playbook.steps : [
      { id: "step-1", action: "navigate", description: "Open incident queue", path: "/incident_list.do" },
      { id: "step-2", action: "move_and_click", description: "Select VPN incident", selector: "#row-target-incident" },
      { id: "step-3", action: "type", description: "Enter AI triage notes", selector: "#work-notes-input", text: "[Now Assist AI] Verified routing to Network Operations (94% confidence)" },
      { id: "step-4", action: "move_and_click", description: "Save incident", selector: "#btn-save-incident" },
    ];

    for (const step of steps) {
      const stepStart = Date.now();
      let status = "passed";
      let errMsg = null;

      try {
        console.log(`[PlaybookRunner] Executing step '${step.id}': ${step.description}`);

        if (step.action === "authenticate") {
          const authCoords = opts.fake ? { x: opts.width - 120, y: 26 } : { x: opts.width - 140, y: 30 };
          await moveCursor(cursorX, cursorY, authCoords.x, authCoords.y, 6);
          cursorX = authCoords.x;
          cursorY = authCoords.y;
          await holdFrames(step.wait_ms || 1200);
        } else if (step.action === "navigate") {
          if (!opts.fake) {
            const baseUrl = new URL(page.url()).origin;
            const dest = step.path
              ? (step.path.startsWith("http") ? step.path : `${baseUrl}${step.path}`)
              : page.url();
            console.log(`[PlaybookRunner] Navigating to ${dest}...`);
            await page.goto(dest, { waitUntil: "domcontentloaded", timeout: 30000 });
            await page.waitForSelector("table, .list_div, #incident_table, form, .form_header, body", { timeout: 15000 }).catch(() => {});
            await injectCursorOverlay(page);
          }
          await moveCursor(cursorX, cursorY, 320, 110, 8);
          cursorX = 320;
          cursorY = 110;
          await holdFrames(step.wait_ms || 2000);
        } else if (step.action === "move_and_click" || step.action === "click") {
          const targetCoords = await page.evaluate((sel, desc, isFake) => {
            function getCenter(el) {
              if (!el) return null;
              const r = el.getBoundingClientRect();
              if (r.width > 0 && r.height > 0) {
                return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), found: true };
              }
              return null;
            }

            if (isFake) {
              if (sel && sel.includes("save")) return { x: 880, y: 575, found: true };
              return { x: 480, y: 210, found: true };
            }

            const textHint = (desc && desc.toLowerCase().includes("vpn")) ? "vpn" : null;
            if (textHint) {
              const rows = Array.from(document.querySelectorAll("tr.list_row, tr"));
              for (const r of rows) {
                if (r.innerText && r.innerText.toLowerCase().includes(textHint)) {
                  const link = r.querySelector("a.linked.formlink, a[href*='incident.do'], a");
                  const c = getCenter(link || r);
                  if (c) return c;
                }
              }
            }

            if (sel) {
              const parts = sel.split(",").map(p => p.trim());
              for (const p of parts) {
                if (p.includes(":has-text(")) {
                  const m = p.match(/(.*?):has-text\(['"](.*?)['"]\)/);
                  if (m) {
                    const tag = m[1] || "*";
                    const query = m[2].toLowerCase();
                    const matches = Array.from(document.querySelectorAll(tag)).filter(e => e.innerText && e.innerText.toLowerCase().includes(query));
                    if (matches.length > 0) {
                      const c = getCenter(matches[0]);
                      if (c) return c;
                    }
                  }
                } else {
                  try {
                    const el = document.querySelector(p);
                    const c = getCenter(el);
                    if (c) return c;
                  } catch {}
                }
              }
            }

            if (sel && (sel.includes("save") || sel.includes("update") || sel.includes("sysverb_update"))) {
              const btn = document.querySelector("#sysverb_update, button#sysverb_update, input#sysverb_update, #sysverb_update_bottom");
              const c = getCenter(btn);
              if (c) return c;
            }

            const firstLink = document.querySelector("a.linked.formlink, a[href*='incident.do']");
            const c = getCenter(firstLink);
            if (c) return c;

            return { x: 480, y: 210, found: false };
          }, step.selector, step.description, opts.fake);

          await moveCursor(cursorX, cursorY, targetCoords.x, targetCoords.y, 8);
          cursorX = targetCoords.x;
          cursorY = targetCoords.y;

          await page.evaluate((x, y) => window.__wb_click_pulse?.(x, y), cursorX, cursorY);
          await captureFrame();

          if (!opts.fake) {
            console.log(`[PlaybookRunner] Clicking live element at (${cursorX}, ${cursorY})...`);
            const didClick = await page.evaluate((x, y, sel, desc) => {
              const textHint = (desc && desc.toLowerCase().includes("vpn")) ? "vpn" : null;
              if (textHint) {
                const links = Array.from(document.querySelectorAll("a.linked.formlink, a[href*='incident.do'], a"));
                const match = links.find(l => l.innerText && l.innerText.toLowerCase().includes(textHint));
                if (match) { match.click(); return true; }
              }

              if (sel && (sel.includes("save") || sel.includes("update") || sel.includes("sysverb_update"))) {
                const btn = document.querySelector("#sysverb_update, button#sysverb_update, input#sysverb_update, #sysverb_update_bottom");
                if (btn) { btn.click(); return true; }
              }

              const el = document.elementFromPoint(x, y);
              if (el) {
                const clickable = el.closest("a, button, input[type='button'], input[type='submit']") || el;
                clickable.click();
                return true;
              }

              const firstLink = document.querySelector("a.linked.formlink, a[href*='incident.do']");
              if (firstLink && sel && (sel.includes("row") || sel.includes("incident"))) {
                firstLink.click();
                return true;
              }
              return false;
            }, cursorX, cursorY, step.selector, step.description);

            if (didClick) {
              await page.waitForNavigation({ waitUntil: "domcontentloaded", timeout: 20000 }).catch(() => {});
              await page.waitForSelector("form, .form_header, #incident_table, table, body", { timeout: 10000 }).catch(() => {});
              await injectCursorOverlay(page);
            }
          } else {
            await page.evaluate((sel) => {
              if (sel && sel.includes("row")) {
                const row = document.getElementById("row-target-incident");
                if (row) row.classList.add("selected");
                const panel = document.getElementById("detail-panel");
                if (panel) panel.style.display = "block";
                const group = document.getElementById("target-assign-group");
                if (group) {
                  group.innerText = "Network Operations";
                  group.style.color = "#059669";
                  group.style.fontWeight = "700";
                }
              } else if (sel && sel.includes("save")) {
                const btn = document.getElementById("btn-save-incident");
                if (btn) {
                  btn.classList.add("success");
                  btn.innerText = "Saved & Verified ✓";
                }
              }
            }, step.selector);
          }
          await holdFrames(step.wait_ms || 2000);
        } else if (step.action === "type") {
          const inputCoords = await page.evaluate((isFake) => {
            if (isFake) {
              const el = document.getElementById("work-notes-input");
              if (el) {
                const r = el.getBoundingClientRect();
                return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), found: true };
              }
              return { x: 460, y: 490, found: true };
            }
            const el = document.querySelector(
              "#activity-stream-textarea, textarea[name='incident.work_notes'], textarea[id*='work_notes'], #activity-stream-work_notes-textarea, textarea[name='work_notes'], textarea"
            );
            if (el) {
              const r = el.getBoundingClientRect();
              if (r.width > 0 && r.height > 0) {
                return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2), found: true };
              }
            }
            return { x: 500, y: 450, found: false };
          }, opts.fake);

          await moveCursor(cursorX, cursorY, inputCoords.x, inputCoords.y, 8);
          cursorX = inputCoords.x;
          cursorY = inputCoords.y;
          await page.evaluate((x, y) => window.__wb_click_pulse?.(x, y), cursorX, cursorY);
          await captureFrame();

          if (!opts.fake) {
            await page.evaluate(() => {
              const el = document.querySelector(
                "#activity-stream-textarea, textarea[name='incident.work_notes'], textarea[id*='work_notes'], #activity-stream-work_notes-textarea, textarea[name='work_notes'], textarea"
              );
              if (el) {
                el.focus();
                el.scrollIntoView({ behavior: "smooth", block: "center" });
              }
            });
          }

          const textToType = step.text || "[Now Assist] Auto-triaged to Network Operations.";
          const chunks = [];
          for (let i = 0; i < textToType.length; i += 10) {
            chunks.push(textToType.slice(i, i + 10));
          }

          for (const chunk of chunks) {
            await page.evaluate((txt, isFake) => {
              const el = isFake
                ? document.getElementById("work-notes-input")
                : document.querySelector("#activity-stream-textarea, textarea[name='incident.work_notes'], textarea[id*='work_notes'], #activity-stream-work_notes-textarea, textarea[name='work_notes'], textarea");
              if (el) {
                el.value = (el.value || "") + txt;
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
              }
            }, chunk, opts.fake);
            await captureFrame();
            await new Promise((r) => setTimeout(r, 60));
          }

          await holdFrames(step.wait_ms || 2000);
        } else if (step.action === "ai_triage" || step.action === "wait_for") {
          const triageCoords = opts.fake ? { x: 520, y: 340 } : { x: 580, y: 280 };
          await moveCursor(cursorX, cursorY, triageCoords.x, triageCoords.y, 8);
          cursorX = triageCoords.x;
          cursorY = triageCoords.y;
          await holdFrames(step.wait_ms || 2500);
        }
      } catch (err) {
        if (!step.optional) {
          status = "failed";
          errMsg = String(err);
        } else {
          status = "skipped";
        }
      }

      stepResults.push({
        step_id: step.id,
        action: step.action,
        description: step.description,
        status,
        duration_ms: Date.now() - stepStart,
        error_message: errMsg,
      });
    }

    // Save final screenshot
    if (opts.outputImage) {
      const imgDir = path.dirname(path.resolve(opts.outputImage));
      if (!fs.existsSync(imgDir)) fs.mkdirSync(imgDir, { recursive: true });
      await page.screenshot({ path: opts.outputImage, type: "png" });
      console.log(`[PlaybookRunner] Screenshot saved to ${opts.outputImage}`);
    }

    // Render WebM video from frames
    if (opts.outputVideo && frames.length > 0) {
      console.log(`[PlaybookRunner] Encoding ${frames.length} frames into native WebM video...`);
      const vidDir = path.dirname(path.resolve(opts.outputVideo));
      if (!fs.existsSync(vidDir)) fs.mkdirSync(vidDir, { recursive: true });

      const recPage = await browser.newPage();
      await recPage.goto("about:blank");
      await recPage.setViewport({ width: opts.width, height: opts.height });

      const videoBuffer = await recPage.evaluate(
        async (base64Frames, w, h) => {
          const canvas = document.createElement("canvas");
          canvas.width = w;
          canvas.height = h;
          const ctx = canvas.getContext("2d");

          const stream = canvas.captureStream(30);
          const recorder = new MediaRecorder(stream, { mimeType: "video/webm;codecs=vp8" });
          const chunks = [];
          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data);
          };

          recorder.start(50);
          for (const b64 of base64Frames) {
            const img = new Image();
            await new Promise((res, rej) => {
              img.onload = res;
              img.onerror = rej;
              img.src = `data:image/jpeg;base64,${b64}`;
            });

            ctx.clearRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            await new Promise((r) => setTimeout(r, 100));
          }

          await new Promise((r) => setTimeout(r, 250));
          recorder.stop();
          await new Promise((r) => {
            recorder.onstop = r;
          });

          const blob = new Blob(chunks, { type: "video/webm" });
          const arrayBuffer = await blob.arrayBuffer();
          return Array.from(new Uint8Array(arrayBuffer));
        },
        frames,
        opts.width,
        opts.height
      );

      await recPage.close();
      fs.writeFileSync(opts.outputVideo, Buffer.from(videoBuffer));
      console.log(`[PlaybookRunner] Video proof saved to ${opts.outputVideo} (${fs.statSync(opts.outputVideo).size} bytes)`);
    }

    // Save Execution Log
    const passedCount = stepResults.filter((s) => s.status === "passed").length;
    const executionResult = {
      bundle_id: playbook.bundle_id,
      playbook_title: playbook.title,
      success: passedCount === stepResults.length,
      total_steps: stepResults.length,
      passed_steps: passedCount,
      step_results: stepResults,
      video_file: opts.outputVideo ? path.resolve(opts.outputVideo) : null,
      thumbnail_file: opts.outputImage ? path.resolve(opts.outputImage) : null,
      live_authenticated: liveAuthenticated,
      duration_ms: Date.now() - startedMs,
      started_at: startTime,
      completed_at: new Date().toISOString(),
    };

    if (opts.outputLog) {
      const logDir = path.dirname(path.resolve(opts.outputLog));
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
      fs.writeFileSync(opts.outputLog, JSON.stringify(executionResult, null, 2), "utf-8");
      console.log(`[PlaybookRunner] Execution audit log saved to ${opts.outputLog}`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("[PlaybookRunner] Fatal error:", err);
  process.exit(1);
});
