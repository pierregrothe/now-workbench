# ADR-011: Unified Async Claude Agent Loop with Streaming Tool Events and Diagnostic Transparency

**Status:** accepted
**Date:** 2026-10-30

## Context

The workbench previously contained two disconnected AI pathways:
1. A synchronous Anthropic client loop in `threads.py` that ran up to 6 tool turns synchronously before
   returning a JSON response, with an unhandled exception fallback that defaulted to static mock templates
   in `tiles.py`.
2. A WebSocket endpoint (`/ws/otto`) that streamed text chunks via `OttoClient` but completely lacked
   tool-calling capabilities, generative UI tile dispatch, and SQLite thread persistence.

Furthermore, silent fallbacks to canned templates caused confusion, giving the impression that live instance
evaluations and media captures were faked when an underlying error occurred.

## Decision

1. **Unified Async Agent Architecture (`AsyncAnthropic`)**:
   - Merge `OttoClient` and `agent.py` into a single async streaming agent engine (`ClaudeAgentRunner`)
     invoked by both REST and WebSocket endpoints.
2. **Anthropic Prompt Caching on Shared Invariants**:
   - Apply `cache_control: {"type": "ephemeral"}` to static system prompts, tool definition schemas,
     and intermediate tool execution checkpoints, cutting input token costs and reducing turn latency.
3. **Real-Time Tool Event Streaming**:
   - Stream granular lifecycle events (`TEXT_DELTA`, `TOOL_CALL_START`, `TOOL_CALL_RESULT`, `TILE_RENDER`)
     so the user sees Claude's tool invocations and live progress in real time rather than waiting for an
     opaque batch response.
4. **Zero Silent Fallbacks in Live Mode**:
   - In live mode (`fake_mode=False`), all exceptions from live instance connections, Table API mutations,
     or Claude API calls must surface explicit diagnostic warning tiles with error details and troubleshooting
     actions. Static simulated responses are strictly prohibited outside of automated unit tests.

## Consequences

- Perceived chat latency drops from 8-12 seconds to sub-second token streaming.
- The UI maintains a single, consistent conversation history in SQLite across all chat surfaces.
- Live instance connectivity issues are immediately visible and actionable instead of masked by mock data.
