# ADR-021: File attachments and conversation limits

**Status:** accepted
**Date:** 2026-11-06

## Context

The owner wants to attach files and chat about them with Otto through the Claude API. They also
want limits on how long a conversation may run and how much it may attach, because testers
spend the owner's Claude key. Decisions taken with the owner on 2026-11-06:
- conversation duration means both a question cap and an age cap;
- 10 MB per file and 25 MB per conversation (at most 10 files);
- administrators set the limits once for everyone.

## Decision

- **Limits are one global setting** (`app_settings`, schema v10), validated by
  `ConversationLimits`. The defaults are 20 questions, 30 days, 10 MB per file, 25 MB and 10
  files per conversation. Administrators edit them in Settings > Conversation limits
  (`PUT /api/limits`). Everyone can read them.
- **Enforced on the server, on every path.** A question past the cap, or in a conversation
  older than the age cap, gets 409 with a reason ("start a new conversation"). This applies to
  the REST and WebSocket chat paths and to uploads. Uploads are read in chunks and stop as soon
  as they pass the per-file cap. Count and total are checked against what the conversation
  already holds.
- **Types come from the bytes.** The accepted types are:
  - PDF;
  - PNG, JPEG, GIF and WebP images;
  - UTF-8 text with a known text extension.

  The name and the browser's claimed type are never trusted.
- **Storage.** Bytes go to `<data>/attachments/<random id>`; no user-supplied name ever touches
  the file system. `chat_attachments` rows are owner-scoped (ADR-018) and cascade with their
  conversation; deleting a conversation deletes its files. Downloads are always served as
  attachments with `nosniff`.
- **What Claude receives.** Files ride with the question they were sent with:
  - PDFs as base64 `document` blocks;
  - images as base64 `image` blocks;
  - text as a `document` with a text source, all placed before the question text.

  Earlier files stay in the context window with their messages, so follow-up questions can
  refer to them. Without a Claude key, Otto says it needs one; files are never silently
  ignored.

## Consequences

- Files resent with later questions cost input tokens each turn. The question and size caps
  bound this, and prompt caching softens it.
- A file can be removed until it is sent; after that it belongs to the conversation history.
