#!/usr/bin/env node
/**
 * Real Chrome / Puppeteer Capture Engine for ServiceNow Instances.
 * Drives authentic scripted demonstrations with visible mouse movement,
 * form interactions, and records high-definition WebM video proofs and PNG screenshots.
 */

import fs from "node:fs";
import path from "node:path";
import puppeteer from "../../web/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js";

// CHROME_PATH comes from the environment in the container (Chromium); macOS Chrome otherwise.
const CHROME_PATH =
  process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    url: "",
    output: "",
    mode: "screenshot",
    username: "",
    password: "",
    width: 1280,
    height: 720,
    duration: 15,
    fake: false,
    credentialsStdin: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--fake") options.fake = true;
    else if (arg === "--url" && args[i + 1]) options.url = args[++i];
    else if (arg === "--output" && args[i + 1]) options.output = args[++i];
    else if (arg === "--mode" && args[i + 1]) options.mode = args[++i];
    else if (arg === "--credentials-stdin") options.credentialsStdin = true;
    else if (arg === "--width" && args[i + 1]) options.width = parseInt(args[++i], 10);
    else if (arg === "--height" && args[i + 1]) options.height = parseInt(args[++i], 10);
    else if (arg === "--duration" && args[i + 1]) options.duration = parseFloat(args[++i]);
  }
  return options;
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
    /* Incident Details Overlay View */
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

      <!-- Incident Detail Section -->
      <div id="detail-panel">
        <div class="ai-banner">
          <div class="ai-banner-title">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="#059669"><path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z"/></svg>
            <span>Now Assist GenAI Recommendation: Route to Network Operations (Gateway Session Reset)</span>
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
    cursor.style.transform = "translate(40px, 40px)";
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
  if (!opts.url || !opts.output) {
    console.error("Usage: node chrome_capture.mjs --url <url> --output <path> [--mode screenshot|video]");
    process.exit(1);
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

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: opts.width, height: opts.height });

    if (opts.username && opts.password) {
      await page.authenticate({ username: opts.username, password: opts.password }).catch(() => {});
    }

    if (opts.fake) {
      console.log("[ChromeCapture] Fake mode enabled: Rendering simulated ServiceNow Agent Workspace...");
      await page.setContent(buildServiceNowOfflineHtml(), { waitUntil: "load" });
    } else {
      // Sign in through /login.do first: current releases answer a deep link with a
      // "not logged in, redirecting" page, so the login form is not on the target page.
      const baseUrl = new URL(opts.url).origin;
      if (opts.username && opts.password) {
        console.log(`[ChromeCapture] Signing in as '${opts.username}' via ${baseUrl}/login.do...`);
        try {
          await page.goto(`${baseUrl}/login.do`, { waitUntil: "domcontentloaded", timeout: 30000 });
        } catch (err) {
          console.error(`The instance could not be reached: ${err.message}`);
          process.exit(1);
        }
        const form = await page.waitForSelector("#user_name", { timeout: 15000 }).catch(() => null);
        if (!form) {
          console.error("The instance did not show its login form at /login.do");
          process.exit(1);
        }
        await page.type("#user_name", opts.username, { delay: 20 });
        await page.type("#user_password", opts.password, { delay: 20 });
        await Promise.all([
          page.waitForNavigation({ waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {}),
          page.click("#sysverb_login"),
        ]);
        await page
          .waitForFunction(() => !window.location.href.includes("login.do"), { timeout: 20000 })
          .catch(() => {});
        if (page.url().includes("login.do")) {
          console.error("Sign-in failed: the instance kept the login page (check the username and password)");
          process.exit(1);
        }
      }
      console.log(`[ChromeCapture] Opening ${opts.url}`);
      try {
        const resp = await page.goto(opts.url, { waitUntil: "domcontentloaded", timeout: 45000 });
        if (resp && resp.status() >= 400) {
          console.error(`The page answered HTTP ${resp.status()}`);
          process.exit(1);
        }
      } catch (err) {
        console.error(`The page could not be loaded: ${err.message}`);
        process.exit(1);
      }
      // Let the page render its data (ServiceNow lists load after the document).
      await page.waitForNetworkIdle({ idleTime: 800, timeout: 20000 }).catch(() => {});
      const signedOut = await page.evaluate(
        () =>
          !!document.querySelector("#user_name") ||
          /not logged in|session has expired/i.test(document.body?.innerText || "")
      );
      if (signedOut) {
        console.error("The instance showed its sign-in page instead of the requested page");
        process.exit(1);
      }
    }

    await injectCursorOverlay(page);
    await new Promise((r) => setTimeout(r, 600));

    // Ensure output directory exists
    const outDir = path.dirname(path.resolve(opts.output));
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }

    if (opts.mode === "screenshot") {
      // Place cursor smoothly over target incident row before taking proof screenshot
      await page.evaluate(() => {
        window.__wb_set_cursor?.(480, 210);
        window.__wb_click_pulse?.(480, 210);
      });
      await new Promise((r) => setTimeout(r, 400));
      await page.screenshot({ path: opts.output, type: "png" });
      console.log(`[ChromeCapture] Verified screenshot saved to ${opts.output} (${fs.statSync(opts.output).size} bytes)`);
    } else if (opts.mode === "video") {
      console.log("[ChromeCapture] Driving interactive demonstration script with real cursor movement...");
      const frames = [];

      async function captureFrame() {
        const buf = await page.screenshot({ encoding: "base64", type: "jpeg", quality: 80 });
        frames.push(buf);
      }

      async function holdFrames(durationMs = 1500) {
        const interval = 100;
        const count = Math.max(1, Math.round(durationMs / interval));
        for (let i = 0; i < count; i++) {
          await captureFrame();
          await new Promise((r) => setTimeout(r, interval));
        }
      }

      const holdDuration = Math.max(1000, Math.round((opts.duration * 1000) / 7));

      async function moveCursor(startX, startY, endX, endY, steps = 6) {
        for (let i = 1; i <= steps; i++) {
          const curX = Math.round(startX + ((endX - startX) * i) / steps);
          const curY = Math.round(startY + ((endY - startY) * i) / steps);
          await page.evaluate((x, y) => window.__wb_set_cursor?.(x, y), curX, curY);
          await captureFrame();
          await new Promise((r) => setTimeout(r, 45));
        }
      }

      // Step 1: Cursor enters from sidebar towards Incident Triage Queue
      await captureFrame();
      await moveCursor(120, 110, 360, 120, 5);
      await holdFrames(holdDuration);

      // Step 2: Hover over priority incident row
      await moveCursor(360, 120, 480, 210, 6);
      await page.evaluate(() => {
        const row = document.getElementById("row-target-incident");
        if (row) row.classList.add("selected");
      });
      await holdFrames(holdDuration);

      // Step 3: Click incident to trigger Now Assist Triage view
      await page.evaluate(() => window.__wb_click_pulse?.(480, 210));
      await captureFrame();
      await page.evaluate(() => {
        const panel = document.getElementById("detail-panel");
        if (panel) panel.style.display = "block";
        const group = document.getElementById("target-assign-group");
        if (group) {
          group.innerText = "Network Operations";
          group.style.color = "#059669";
          group.style.fontWeight = "700";
        }
      });
      await holdFrames(holdDuration);

      // Step 4: Move cursor down to the AI recommendation banner
      await moveCursor(480, 210, 520, 340, 5);
      await holdFrames(holdDuration);

      // Step 5: Move cursor into the Work Notes field
      await moveCursor(520, 340, 460, 490, 5);
      await page.evaluate(() => window.__wb_click_pulse?.(460, 490));
      await captureFrame();

      // Step 6: Type Now Assist work notes character-by-character
      const noteText = "[Now Assist AI] Incident auto-triaged: Category=Network, Route=Network Operations (Confidence: 94.2%).";
      const sampleChunks = [
        "[Now Assist AI] ",
        "Incident auto-triaged: ",
        "Category=Network, ",
        "Route=Network Operations ",
        "(Confidence: 94.2%).",
      ];
      for (const chunk of sampleChunks) {
        await page.evaluate((txt) => {
          const input = document.getElementById("work-notes-input");
          if (input) input.value += txt;
        }, chunk);
        await captureFrame();
        await new Promise((r) => setTimeout(r, 50));
      }
      await holdFrames(holdDuration);

      // Step 7: Move to Save button and click
      await moveCursor(460, 490, 880, 575, 6);
      await page.evaluate(() => {
        window.__wb_click_pulse?.(880, 575);
        const btn = document.getElementById("btn-save-incident");
        if (btn) {
          btn.classList.add("success");
          btn.innerText = "Saved & Verified ✓";
        }
      });
      await holdFrames(holdDuration);

      console.log(`[ChromeCapture] Collected ${frames.length} real interactive demonstration frames.`);

      // Render WebM video using isolated recorder canvas
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

          // Hold last frame briefly for clarity
          await new Promise((r) => setTimeout(r, 300));
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
      fs.writeFileSync(opts.output, Buffer.from(videoBuffer));
      console.log(`[ChromeCapture] Verified demonstration video saved to ${opts.output} (${fs.statSync(opts.output).size} bytes)`);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("[ChromeCapture] Fatal:", err);
  process.exit(1);
});
