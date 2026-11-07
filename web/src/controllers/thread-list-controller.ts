// web/src/controllers/thread-list-controller.ts
// ReactiveController for the sidebar's conversation list: load, create, archive, delete.
// Author: Pierre Grothe
// Date: 2026-11-07
//
// ADR-024: the shell kept this list and its four API calls inline. Every failure is kept in
// `error` and shown; a failed load never pretends the list is empty or current (ADR-013).

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import type { NavThreadItem } from '../components/now-nav-rail.js';

interface ThreadRecord {
  id: string;
  title: string;
  archived?: boolean;
  target_tab?: string;
  tokens_used?: number;
  max_tokens?: number;
}

export class ThreadListController implements ReactiveController {
  private readonly host: ReactiveControllerHost;

  /** The owner's conversations, archived ones included. */
  items: NavThreadItem[] = [];
  /** The last failure, or '' after a successful call. */
  error = '';

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {
    void this.load();
  }

  /** Reload the list from the server. */
  async load(): Promise<void> {
    const res = await this.request('load conversations', '/api/threads?include_archived=true', {});
    if (!res) return;
    const list = (await res.json()) as ThreadRecord[];
    this.items = list.map((t) => ({
      id: t.id,
      title: t.title,
      targetTab: t.target_tab || 'home',
      archived: Boolean(t.archived),
      tokensUsed: t.tokens_used ?? 0,
      maxTokens: t.max_tokens ?? 2000000,
    }));
    this.host.requestUpdate();
  }

  /** Create a conversation (optionally with a first message); return its id, or null. */
  async create(title: string, firstMessage?: string): Promise<string | null> {
    const created = await this.request('create conversation', '/api/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, target_tab: 'home' }),
    });
    if (!created) return null;
    const { id } = (await created.json()) as { id: string };
    if (firstMessage !== undefined) {
      const sent = await this.request('send message', `/api/threads/${id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: firstMessage, role: 'user' }),
      });
      if (!sent) {
        await this.load();
        return null;
      }
    }
    await this.load();
    return id;
  }

  /** Archive or restore a conversation; true when the server accepted it. */
  async setArchived(threadId: string, archived: boolean): Promise<boolean> {
    const res = await this.request(
      archived ? 'archive conversation' : 'unarchive conversation',
      `/api/threads/${threadId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived }),
      }
    );
    if (res) await this.load();
    return res !== null;
  }

  /** Delete a conversation; true when the server accepted it. */
  async remove(threadId: string): Promise<boolean> {
    const res = await this.request('delete conversation', `/api/threads/${threadId}`, {
      method: 'DELETE',
    });
    if (res) await this.load();
    return res !== null;
  }

  private async request(action: string, url: string, init: RequestInit): Promise<Response | null> {
    try {
      const res = await fetch(url, init);
      this.error = res.ok ? '' : `Could not ${action}: HTTP ${res.status}`;
      this.host.requestUpdate();
      return res.ok ? res : null;
    } catch (err) {
      this.error = `Could not ${action}: ${err instanceof Error ? err.message : String(err)}`;
      this.host.requestUpdate();
      return null;
    }
  }
}
