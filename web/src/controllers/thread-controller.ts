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
  /** Tool runs Otto performed for this reply (from the backend, never invented). */
  steps?: { label: string; ok: boolean }[];
  tokens_in?: number;
  tokens_out?: number;
  cost_estimate?: number;
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
    steps: m.widget_data?.steps || [],
  }));
}

export class ThreadController implements ReactiveController {
  private host: ReactiveControllerHost;
  public threadId: string = '';
  public messages: ChatMessage[] = [];
  public isStreaming: boolean = false;
  public error: string | null = null;
  /** Called after a conversation was created implicitly by the first message. */
  public onThreadCreated: ((threadId: string) => void) | null = null;

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
    this.threadId = threadId;
    this.messages = [];
    this.error = null;
    this.host.requestUpdate();

    if (!threadId) return;

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
    if (!promptText.trim()) return null;

    const userMsg: ChatMessage = {
      sender: 'user',
      text: promptText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    this.messages = [...this.messages, userMsg];
    this.isStreaming = true;
    this.error = null;
    this.host.requestUpdate();

    try {
      let createdThreadId = '';
      if (!this.threadId) {
        createdThreadId = await this.createThread(promptText);
        this.threadId = createdThreadId;
      }
      const res = await fetch(`/api/threads/${encodeURIComponent(this.threadId)}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: promptText, ...widget }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      // The backend returns the full chronological history, including the new reply.
      const history = mapThreadRecords(await res.json());
      const agentMsg = [...history].reverse().find((m) => m.sender === 'agent') ?? null;
      this.messages = history;
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

  /** Show a local note in the conversation without calling the backend. */
  addSystemNote(text: string): void {
    this.messages = [...this.messages, { sender: 'system', text }];
    this.host.requestUpdate();
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
    this.threadId = '';
    this.error = null;
    this.host.requestUpdate();
  }
}
