---
id: PRD-003
title: Per-user ownership, groups, approved sharing and versions
status: draft
date: 2026-11-06
adrs: [ADR-016, ADR-017, ADR-018]
charter_link: charter.md#1-vision--purpose
milestone: unscheduled (in progress)
---

# PRD-003: Per-user ownership, groups, approved sharing and versions

## Problem
The workbench is about to have testers from outside the owner's household. Today every
conversation, demo bundle, ServiceNow instance, seed run and preference is global: any signed-in
person sees and changes everyone's work, and can use instance credentials someone else entered.
There is also no way to hand a finished demo to a team, and no history of a demo's changes.

## Users
- **Solution Consultant:** builds demos, wants them private until ready, then shares them.
- **Group administrator:** runs a region, territory or business unit; decides who joins the
  group and which artifacts reach its members.
- **Administrator:** creates groups, appoints group administrators, approves anything shared
  with everyone.

## Requirements (decisions taken with the owner, 2026-11-06)
1. **Everything is per user.** Conversations, demo bundles (Artifact library), ServiceNow
   instances with their credentials, seed history and preferences belong to the person who
   created them. Nobody else sees them, administrators included. The Claude API key stays one
   shared secret managed by administrators.
2. **Owner CRUD.** The owner of an object can create, read, update and delete it.
3. **Groups.** Administrators create groups of three kinds: region, territory, business unit.
   A person can belong to several groups. People ask to join; a group administrator (or an
   administrator) accepts or declines. Administrators appoint group administrators.
4. **Sharing with approval.** An owner shares an artifact with a group (approved by that
   group's administrator) or with everyone (approved by an administrator). Approvers sharing
   to a target they approve are approved immediately. Recipients get read-only use: open,
   inspect, export, run against their own instances, and clone into a copy they own.
5. **Versions.** Saving a version freezes the artifact as an immutable snapshot (v1, v2, ...).
   Shares point at a version. A new version must be approved again for every target; until
   then recipients keep the last approved version.
6. **Interface:** the Artifact library marks owned and shared artifacts and their version; a
   share dialog picks a group or everyone; Settings gains Groups and Approvals sections.

## Out of scope (this PRD)
Sharing conversations or instances; per-user Claude usage limits (tracked separately);
diffing two versions; restoring an old version over the working copy.

## Acceptance
- [ ] Two users never see each other's conversations, instances, seed runs or bundles.
- [ ] A group share is invisible to members until the group admin approves it.
- [ ] A global share needs an administrator.
- [ ] Saving v2 of a shared artifact leaves recipients on v1 until v2 is approved.
- [ ] Recipients cannot modify, delete, re-share or capture into a shared artifact.
- [ ] Join requests need a group administrator's acceptance.
- [ ] Existing data migrates to the first administrator.
