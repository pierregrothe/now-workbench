// web/src/controllers/thread-controller.ts
// ReactiveController managing Otto threads, message history, and prompt submissions.
// Author: Pierre Grothe
// Date: 2026-10-31

import type { ReactiveController, ReactiveControllerHost } from 'lit';

export interface ChatMessage {
  id?: string;
  sender: 'user' | 'agent' | 'system';
  text: string;
  timestamp?: string;
  tiles?: any[];
  /** How the reply lays its tiles out ('1-col', '2-col', '3-col' or 'auto'). */
  layout?: string;
  /** Interface commands Otto sent with this reply (ADR-026); applied on arrival only. */
  ui?: { type: string; [key: string]: unknown }[];
  /** Tool runs Otto performed for this reply (from the backend, never invented). */
  steps?: { label: string; ok: boolean }[];
  /** The owner's stored rating and comment on an Otto reply (null when not rated). */
  feedback?: { rating: 'up' | 'down'; comment: string } | null;
  tokens_in?: number;
  tokens_out?: number;
  cost_estimate?: number;
}

/** A file waiting to be sent with the next question (ADR-021). */
export interface PendingAttachment {
  id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
}

/** The server's explanation for a failed request, or the HTTP status. */
async function failure(res: Response): Promise<Error> {
  const body = await res.json().catch(() => ({}));
  const detail = (body as { detail?: unknown }).detail;
  return new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`);
}

/** Map the backend's bare ChatMessageRecord[] into view messages. */
function mapThreadRecords(data: unknown): ChatMessage[] {
  if (!Array.isArray(data)) {
    throw new Error('Unexpected thread response shape');
  }
  return data.map((m: any) => ({
    id: m.id,
    sender: m.role === 'assistant' ? 'agent' : m.role || 'user',
    text: m.content || '',
    timestamp: new Date(m.created_at || Date.now()).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
    tiles: m.widget_data?.tiles || [],
    layout: m.widget_data?.layout,
    ui: m.widget_data?.ui || [],
    steps: m.widget_data?.steps || [],
    feedback: m.feedback ?? null,
  }));
}

export class ThreadController implements ReactiveController {
  private host: ReactiveControllerHost;
  public threadId: string = '';
  public messages: ChatMessage[] = [];
  public isStreaming: boolean = false;
  public error: string | null = null;
  /** Title of the active conversation, as stored by the backend. */
  public title: string = '';
  /** Called after a conversation was created implicitly by the first message. */
  public onThreadCreated: ((threadId: string) => void) | null = null;
  /** Files uploaded and waiting to go out with the next question. */
  public pending: PendingAttachment[] = [];
  public isUploading: boolean = false;
  /** Why the last upload failed, shown next to the prompt. */
  public attachError: string = '';
  /** The monthly-allowance warning (ADR-031) from the last answer, shown next to the prompt. */
  public usageWarning: string = '';

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {
    // Can auto-load thread if threadId set
  }

  hostDisconnected(): void {
    // Clean up any streaming connections
  }

  async setThread(threadId: string): Promise<void> {
    // Opening the conversation the first question just created keeps that answer's warning.
    if (threadId !== this.threadId) this.usageWarning = '';
    this.threadId = threadId;
    this.messages = [];
    this.title = '';
    this.error = null;
    this.host.requestUpdate();

    if (!threadId) return;

    void this.loadTitle(threadId);

    try {
      const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/messages`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      this.messages = mapThreadRecords(await res.json());
    } catch (err: any) {
      this.error = `Could not load thread messages: ${err.message || 'unknown error'}`;
      this.messages = [{ sender: 'system', text: this.error }];
    } finally {
      this.host.requestUpdate();
    }
  }

  async sendMessage(
    promptText: string,
    widget?: { widget_type: string; widget_data: Record<string, unknown> }
  ): Promise<ChatMessage | null> {
    if (!promptText.trim() && this.pending.length === 0) return null;
    const attachmentIds = widget ? [] : this.pending.map((a) => a.id);

    const userMsg: ChatMessage = {
      sender: 'user',
      text: promptText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    this.messages = [...this.messages, userMsg];
    this.isStreaming = true;
    this.error = null;
    this.usageWarning = '';
    this.host.requestUpdate();

    try {
      let createdThreadId = '';
      if (!this.threadId) {
        createdThreadId = await this.createThread(promptText || 'New Otto Conversation');
        this.threadId = createdThreadId;
      }
      const res = await fetch(`/api/threads/${encodeURIComponent(this.threadId)}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: promptText, ...widget, attachment_ids: attachmentIds }),
      });

      if (!res.ok) {
        throw await failure(res);
      }
      if (attachmentIds.length) this.pending = [];

      // The backend returns the full chronological history, including the new reply. A long
      // reply streams keep-alive spaces first; an error found after that arrives as {detail}.
      const body = await res.json();
      if (!Array.isArray(body) && typeof body?.detail === 'string') {
        throw new Error(body.detail);
      }
      const history = mapThreadRecords(body);
      const agentMsg = [...history].reverse().find((m) => m.sender === 'agent') ?? null;
      this.messages = history;
      this.usageWarning = res.headers.get('X-Usage-Warning') ?? '';
      if (createdThreadId) {
        this.onThreadCreated?.(createdThreadId);
      }
      return agentMsg;
    } catch (err: any) {
      this.error = `Could not send message: ${err.message || 'unknown error'}`;
      const errMsg: ChatMessage = {
        sender: 'system',
        text: this.error,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      this.messages = [...this.messages, errMsg];
      return null;
    } finally {
      this.isStreaming = false;
      this.host.requestUpdate();
    }
  }

  /** Upload files for the next question, starting a conversation if there is none. */
  async attach(files: File[]): Promise<void> {
    if (files.length === 0) return;
    this.isUploading = true;
    this.error = null;
    this.attachError = '';
    this.host.requestUpdate();
    let createdHere = '';
    try {
      if (!this.threadId) {
        createdHere = await this.createThread('New Otto Conversation');
        this.threadId = createdHere;
      }
      for (const file of files) {
        const url = `/api/threads/${encodeURIComponent(this.threadId)}/attachments?filename=${encodeURIComponent(file.name)}`;
        const res = await fetch(url, { method: 'POST', body: file });
        if (!res.ok) throw await failure(res);
        this.pending = [...this.pending, (await res.json()) as PendingAttachment];
      }
      if (createdHere) this.onThreadCreated?.(createdHere);
    } catch (err: any) {
      this.attachError = `Could not attach the file: ${err.message || 'unknown error'}`;
      if (createdHere && this.pending.length === 0) {
        // Nothing was attached: do not leave an empty conversation behind.
        await fetch(`/api/threads/${encodeURIComponent(createdHere)}`, { method: 'DELETE' });
        this.threadId = '';
      } else if (createdHere) {
        this.onThreadCreated?.(createdHere);
      }
    } finally {
      this.isUploading = false;
      this.host.requestUpdate();
    }
  }

  /** Remove a file that has not been sent yet. */
  async detach(id: string): Promise<void> {
    const url = `/api/threads/${encodeURIComponent(this.threadId)}/attachments/${encodeURIComponent(id)}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (res.ok) {
      this.pending = this.pending.filter((a) => a.id !== id);
    } else {
      this.addSystemNote(`Could not remove the file: ${(await failure(res)).message}`);
    }
    this.host.requestUpdate();
  }

  /** Show a local note in the conversation without calling the backend. */
  addSystemNote(text: string): void {
    this.messages = [...this.messages, { sender: 'system', text }];
    this.host.requestUpdate();
  }

  private async loadTitle(threadId: string): Promise<void> {
    try {
      const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}`);
      if (res.ok && this.threadId === threadId) {
        this.title = ((await res.json()) as { title?: string }).title ?? '';
        this.host.requestUpdate();
      }
    } catch {
      // The breadcrumb falls back to the first prompt; the conversation itself still loads.
    }
  }

  private async createThread(firstPrompt: string): Promise<string> {
    const res = await fetch('/api/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: firstPrompt.slice(0, 40) }),
    });
    if (!res.ok) {
      throw new Error(`could not start a conversation (HTTP ${res.status})`);
    }
    const created = (await res.json()) as { id?: string };
    if (!created.id) {
      throw new Error('unexpected response when starting a conversation');
    }
    return created.id;
  }

  clear(): void {
    this.messages = [];
    this.pending = [];
    this.threadId = '';
    this.error = null;
    this.host.requestUpdate();
  }
}
