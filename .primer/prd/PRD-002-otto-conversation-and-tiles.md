---
id: PRD-002
title: Otto-style conversation and tiles
status: draft
date: 2026-11-06
adrs: [ADR-013]
charter_link: charter.md#1-vision--purpose
milestone: unscheduled (in progress)
---

# PRD-002: Otto-style conversation and tiles

## Problem
Our chat and tiles were built as a prototype and do not communicate the way ServiceNow
Otto does. Observed on the Otto product page and its demo video (reviewed 2026-11-06 in
a real browser): Otto answers with a short line of text plus purpose-built tiles, shows
what it did as a collapsible "Thought for a moment, N steps" list, asks for approval on
a card, and shows the outcome on a card. Ours shows raw text bubbles, cards whose
buttons do nothing after use, and no visible agent work.

## Users
Solution Consultants and developers using Otto inside now-workbench.

## Observed reference (the alignment target)
- **Home:** a sparkle glyph and a short greeting ("Hi <name>, let's get it done."), one
  large rounded prompt pill with a "+" at the left and a round green send button, a row
  of rounded grey suggestion chips, and a grid of rounded tiles on a soft blue-grey
  gradient. Tiles carry a title and an open-arrow at the top right.
- **Conversation:** the assistant is a sparkle glyph, its name and a timestamp, then
  text; the user is a light rounded bubble on the right with an avatar.
- **Agent work:** a collapsible "Thought for a moment, 4 steps" row; expanded, a vertical
  checklist (check circles joined by a thin line, a spinner on the active step).
- **Approval:** a card with the plan, then "Edit details" and a primary "Submit" action.
  After the decision the card shows a status ("Approved", a progress bar, "All confirmed")
  and a full-width secondary action ("View all ... requests").
- **Result tiles:** list cards with avatar rows and small status chips ("Pending"),
  progress cards, chart cards; a one-line Otto note with the sparkle inside a card.
- **Layout:** chat on the left, an open item or result in a panel on the right; the
  prompt reads "Ask anything or search" with a footnote that answers are AI-generated.
- **Brand:** dark navy surfaces, ServiceNow green accents, purple and blue gradients,
  bold geometric sans-serif headings.

## In Scope (must-haves)
- Assistant messages show the Otto sparkle, name and time; the user is a light bubble.
- A collapsible agent-steps row built from the tools Otto actually ran (never invented).
- Approval cards are one-shot: Confirm or Cancel replaces the card with its outcome.
- The chat scrolls to the newest reply; the prompt carries an AI-accuracy footnote.
- Tiles share one card chrome (title, open-arrow, status chip, progress) and keep the
  Lux tokens in `web/src/styles/lux-theme.css`.
- Every tile button either works or is not rendered.
- The other workbench screens follow the ADR-019 measurements. Restyled: Synthesizer and
  Media Capture (story 2026.11b.02, 2026-11-07); Fluent Explorer and the Artifact library
  cards (story 2026.11b.03, 2026-11-07). Still to do: the Settings Instances buttons
  (`admin-shared-styles`), the admin panel canvas, and the share, clone and deploy dialogs
  (inline styles, 6px inputs).

## Out of Scope (anti-creep fence)
- We will NOT copy ServiceNow's text, logos, artwork or product screenshots; we align
  structure and behavior, using our own words and Lux tokens.
- We will NOT add voice or a mobile layout in this PRD.
- We will NOT fabricate steps, results or status: every step and tile comes from a real
  tool run or backend response (ADR-013).
- We will NOT build a second chat component; the existing chat view evolves.

## Acceptance Criteria
- [ ] Playwright spec: a tool-using reply shows "N steps" and expands to the real tools.
- [ ] Playwright spec: Confirm and Cancel each replace the approval card with an outcome.
- [ ] Playwright spec: the newest reply is scrolled into view.
- [ ] Every tile action present in the UI has a spec proving it does something.
- [ ] Screenshots of home, conversation and an approval card reviewed by the owner.

## Success Metrics
- Owner sign-off on screenshots against the observed reference.
- Zero dead buttons in a walk through all tile types.

## Dependencies
- ADR-013 (UI testing, no fabricated state); PRD-001 (future optimization tiles).

## Out of Library Scope (always)
ServiceNow-hosted Otto behavior; we only mirror the interaction pattern locally.

## Open Questions
- Side panel (chat plus open item): in this PRD or a follow-up?
- Home tile grid: which live tiles (instances, bundles, recent runs) belong on Home?
- Should the user name and avatar come from a profile setting instead of "Pierre Grothe"?
