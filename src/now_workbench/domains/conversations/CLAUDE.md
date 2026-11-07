# conversations domain context (Claude-only)

## What this domain does

Stores Otto conversations: threads, their messages (with the exact Claude transcript of each
assistant reply), the files attached to them, the thumbs up or down people give Otto's replies,
and the one global set of conversation limits administrators edit. It checks whether a thread may take another question, stores and types
attachments, and turns them into Messages API content blocks. It does NOT call Claude or build
replies (`interfaces/ai/` and `interfaces/api/replies.py`), enforce the monthly allowance
(`telemetry` counts it, `interfaces/api/allowance.py` gates on it), or decide who is signed in
(`identity` and the access middleware).

## Public entry points (all from `now_workbench.domains.conversations`)

- Repositories: `ThreadRepository` (threads and messages), `ChatRepository` (limits and
  attachment rows) and `FeedbackRepository` (reply ratings). All take a connection.
- `ThreadRepository` methods: `list_threads`, `get_thread`, `create_thread`, `update_thread`,
  `delete_thread`, `list_messages`, `add_message(msg, transcript=None)`, `list_transcripts`
  (message id -> stored transcript), `add_thread_tokens`, `daily_question_counts(since)`.
- `FeedbackRepository` methods: `message_role`, `put(message_id, rating, comment)` (upsert,
  False unless an assistant reply in the owner's thread), `get`, `list_own`, `list_all`
  (unscoped: callers check the role).
- `ChatRepository` methods: `get_conversation_limits`, `put_conversation_limits`,
  `add_attachment`, `list_attachments`, `get_attachment`, `attach_to_message`,
  `delete_attachment` (row only).
- Services shared by the API and Otto's tools (raise `platform/errors.py` errors):
  `update_conversation` (rename/archive/restore, `NotFoundError`), `delete_conversation`
  (thread, cascaded rows, then the files on disk), `remove_attachment` (unsent files only,
  `ConflictError` once sent), `rate_reply(conn, message_id, FeedbackCreate)` (`NotFoundError`
  for a message not yours, `InvalidInputError` for a non-assistant message), and
  `list_feedback(conn, actor)` (everyone's for administrators, otherwise your own).
- Limits: `get_limits(conn)`, `set_limits(conn, actor, limits)` (administrators only).
- Files: `check_can_ask(thread, limits)`, `store_attachment(thread_id, filename, data,
  existing, limits)` -> unsaved `Attachment`, `read_bytes`, `delete_files`, `claude_blocks`.
  Errors: `LimitReachedError`, `UnsupportedFileError` (both `ValueError`).
- Models: `ChatThreadCreate`, `ChatThreadUpdate`, `ChatThreadRecord`, `ChatMessageCreate`,
  `ChatMessageRecord` (carries the stored `rating`), `Attachment`, `ConversationLimits`,
  `FeedbackCreate`, `MessageFeedback`; constant
  `MAX_THREAD_CONTEXT_MESSAGES` (20, the history window callers slice).

## Wiring

- Tables: chat_threads, chat_messages, chat_attachments and message_feedback (v15, one row
  per reply, cascades from its message; the others cascade on thread delete; `PRAGMA foreign_keys` is on in `db_session`), and the `conversation_limits` row of
  app_settings (JSON payload). Attachment bytes live in files under
  `settings.get_data_dir()` / `attachments`, named by a random `att-` id.
- Both repositories derive from `Repository` in `platform/db/repository.py`.
- Imported by `interfaces/api/threads.py`, `attachments.py`, `feedback.py`, `otto_ws.py`, `replies.py`,
  `allowance.py`, `usage.py`, and `interfaces/ai/conversation.py`, `tools/account.py`,
  `tools/admin.py`, `tools/confirm.py`, `tools/history.py`. No other domain imports it.
- It imports `identity` (`AuthUser`, `require_admin`), `profile` (`sniff_image`), and from
  platform `current_owner`, `settings`, the `Repository` base and the domain errors.
- Contracts: `acyclic-domains` -- `identity` and `profile` must never import this domain.

## Invariants and gotchas

- Owner scoping (ADR-018): every thread, message and attachment read or write is gated on
  `current_owner()`, which raises `NoOwnerError` outside an owner scope (fail closed).
  `create_thread` with an id another owner holds silently mints a new id rather than
  touching their row. `add_message` raises `LookupError` for a thread that is not yours.
- Limits are global, not per owner: `get_conversation_limits` returns the defaults until an
  administrator saves them. `set_limits` calls `require_admin` (raises `ForbiddenError`);
  the HTTP route also guards with `require_role` on `Role.ADMIN`.
- `ConversationLimits.monthly_allowance_tokens` is stored here but enforced elsewhere
  (`interfaces/api/allowance.py`).
- `ChatThreadRecord.max_tokens` is not stored: the thread queries read
  `max_conversation_tokens` out of app_settings with a hard-coded 2,000,000 fallback that
  duplicates the model default. Change both together.
- `check_can_ask` refuses on the token budget (`tokens_used` vs `max_conversation_tokens`) or
  thread age (`max_age_days`). Callers skip it for a `tool_confirm` message (confirming an
  action is not a new question). Upload routes call it too.
- Prompt caching (ADR-023): replay the transcripts from `list_transcripts` unchanged so the
  prefix stays byte-identical and Claude serves it from cache. `compact_at_tokens` is passed
  to the agent for server-side compaction; `tokens_used` is billed tokens (cached input at a
  tenth), added after each reply with `add_thread_tokens` (negatives clamp to 0).
- Attachment type comes from the bytes only (PDF, PNG/JPEG/WebP via `sniff_image`, GIF, or
  UTF-8 text with a known text suffix); the client's content type is ignored, its file name
  only supplies the suffix gate for text files, and the stored file name is the id, never the
  user's name. `store_attachment` writes the bytes but
  does not insert the row: call `add_attachment` with what it returns.
- An attachment is "sent" once `attach_to_message` sets its `message_id`; after that
  `remove_attachment` refuses. `claude_blocks` reads the bytes from disk on every call, and
  sent files are replayed with their message each turn.
- `delete_attachment` and `delete_thread` remove rows only; delete the files with
  `delete_files` (the services already do this in the right order).

- Feedback never leaves the workbench (no external service). Rating again replaces the row
  (rating and comment), so a reply has at most one rating. `list_messages` LEFT JOINs it in.

## Do not reinvent

- Content-type sniffing for uploads (`store_attachment` applies it; `sniff_image` in `profile`).
- Building Claude document/image blocks from stored files (`claude_blocks`).
- Per-day question counts for charts (`daily_question_counts`), and the token budget and age
  check (`check_can_ask`).
- Reading the limits: use `get_limits` or `get_conversation_limits`, never app_settings SQL.
