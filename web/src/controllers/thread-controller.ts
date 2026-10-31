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
  tokens_in?: number;
  tokens_out?: number;
  cost_estimate?: number;
}

export class ThreadController implements ReactiveController {
  private host: ReactiveControllerHost;
  public threadId: string = '';
  public messages: ChatMessage[] = [];
  public isStreaming: boolean = false;
  public error: string | null = null;

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
      if (res.ok) {
        const data = await res.json();
        this.messages = (data.messages || []).map((m: any) => ({
          id: m.id,
          sender: m.role === 'assistant' ? 'agent' : m.role || 'user',
          text: m.content || '',
          timestamp: m.created_at || new Date().toISOString(),
          tiles: m.metadata?.tiles || [],
          tokens_in: m.metadata?.tokens_in,
          tokens_out: m.metadata?.tokens_out,
          cost_estimate: m.metadata?.cost_estimate,
        }));
      }
    } catch (err: any) {
      this.error = err.message || 'Failed to load thread messages';
    } finally {
      this.host.requestUpdate();
    }
  }

  async sendMessage(promptText: string, metadata: Record<string, any> = {}): Promise<ChatMessage | null> {
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
      const endpoint = this.threadId
        ? `/api/threads/${encodeURIComponent(this.threadId)}/messages`
        : '/api/otto/chat';

      const payload = this.threadId
        ? { content: promptText, metadata }
        : { prompt: promptText, ...metadata };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      const agentMsg: ChatMessage = {
        id: data.id,
        sender: 'agent',
        text: data.content || data.response || data.summary || '',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        tiles: data.tiles || data.metadata?.tiles || [],
        tokens_in: data.tokens_in || data.metadata?.tokens_in,
        tokens_out: data.tokens_out || data.metadata?.tokens_out,
        cost_estimate: data.cost_estimate || data.metadata?.cost_estimate,
      };

      this.messages = [...this.messages, agentMsg];
      return agentMsg;
    } catch (err: any) {
      this.error = err.message || 'Failed to send message';
      const errMsg: ChatMessage = {
        sender: 'system',
        text: `Error: ${this.error}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      this.messages = [...this.messages, errMsg];
      return null;
    } finally {
      this.isStreaming = false;
      this.host.requestUpdate();
    }
  }

  clear(): void {
    this.messages = [];
    this.threadId = '';
    this.error = null;
    this.host.requestUpdate();
  }
}
