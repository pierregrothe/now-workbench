// web/src/utils/intent-router.ts
// Routes a typed prompt to the workbench screen it is about (keyword rules, no model call).
// Author: Pierre Grothe
// Date: 2026-11-07

/** Where a prompt was routed and why (shown to the user). */
export interface DetectedIntent {
  tab: string;
  menuLabel: string;
  explanation: string;
  isQuestion?: boolean;
}

/** Pick the screen a prompt belongs to; questions stay with Otto. */
export function detectIntent(prompt: string): DetectedIntent {
  const lower = prompt.toLowerCase().trim();

  // 1. Informational Questions & Conversational Otto Sessions
  const isQuestion =
    lower.endsWith('?') ||
    lower.startsWith('what') ||
    lower.startsWith('how') ||
    lower.startsWith('why') ||
    lower.startsWith('where') ||
    lower.startsWith('who') ||
    lower.startsWith('when') ||
    lower.startsWith('which') ||
    lower.startsWith('can ') ||
    lower.startsWith('could ') ||
    lower.startsWith('would ') ||
    lower.startsWith('tell me') ||
    lower.startsWith('explain') ||
    lower.startsWith('describe') ||
    lower.startsWith('help') ||
    lower.startsWith('is ') ||
    lower.startsWith('are ') ||
    lower.startsWith('does ') ||
    lower.startsWith('do ') ||
    lower.startsWith('show ') ||
    lower.startsWith('review ') ||
    lower.startsWith('investigate') ||
    lower.includes('what is') ||
    lower.includes('what are') ||
    lower.includes('how do') ||
    lower.includes('how can') ||
    lower.includes('how to') ||
    lower.includes('tell me about') ||
    lower.includes('instande') ||
    lower.includes('recipe') ||
    lower.includes('update set') ||
    lower.includes('demohub');

  if (isQuestion) {
    return {
      tab: 'home',
      menuLabel: 'Otto AI Copilot',
      explanation: 'Conversational question -> Answered by Otto AI Copilot',
      isQuestion: true,
    };
  }

  // 2. Explicit Navigation Commands to Settings
  const isExplicitSettings =
    (lower.startsWith('go to') ||
      lower.startsWith('open') ||
      lower.startsWith('navigate to') ||
      lower === 'settings' ||
      lower === 'admin') &&
    (lower.includes('setting') ||
      lower.includes('admin') ||
      lower.includes('config') ||
      lower.includes('instance') ||
      lower.includes('preference'));

  if (isExplicitSettings) {
    return {
      tab: 'admin',
      menuLabel: 'Instance Settings',
      explanation: 'Explicit navigation -> Opening Workbench Settings',
    };
  }

  // 3. Media Capture Intent
  if (
    lower.includes('screenshot') ||
    lower.includes('video') ||
    lower.includes('capture') ||
    lower.includes('.webm') ||
    lower.includes('.png') ||
    lower.includes('record')
  ) {
    return {
      tab: 'capture',
      menuLabel: 'Media Capture',
      explanation: `Detected media capture intent -> Routed to Media Capture for "${prompt.slice(0, 64)}"`,
    };
  }

  // 4. Fluent SDK Schema Intent
  if (
    lower.includes('fluent') ||
    lower.includes('schema') ||
    lower.includes('.now.ts') ||
    lower.includes('diff') ||
    lower.includes('column')
  ) {
    return {
      tab: 'fluent',
      menuLabel: 'Fluent SDK Explorer',
      explanation: 'Detected Fluent schema intent -> Routed to Fluent SDK Explorer',
    };
  }

  // 5. Artifact Library / Demo Catalog Intent
  if (
    lower.includes('catalog') ||
    lower.includes('artifact') ||
    lower.includes('library') ||
    lower.includes('rollback') ||
    lower.includes('unseed')
  ) {
    return {
      tab: 'artifacts',
      menuLabel: 'Artifact Library',
      explanation: 'Detected bundle catalog intent -> Routed to Artifact Library',
    };
  }

  // 6. Default to Use-Case Synthesis
  return {
    tab: 'synthesizer',
    menuLabel: 'Use-Case Synthesizer',
    explanation: 'Detected use-case demo synthesis intent -> Routed to Use-Case Synthesizer & SC Narrative Studio',
  };
}
