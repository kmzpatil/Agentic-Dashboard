# ATLAS Feature

ATLAS analytics interface for asking natural-language questions about dashboard data.

## Main Module

- File: `TalkToDataModule.jsx`
- Export: default React component `TalkToDataModule`
- Purpose: chat-driven analysis with conversation history, markdown answers, optional artifact canvas, and voice input.

## Component Contract

```jsx
<TalkToDataModule
  authToken={authToken}
  routeState={routeState}
  onNavigate={onNavigate}
/>
```

### Props
- `authToken` (`string | null`): bearer token forwarded to assistant/conversation APIs.
- `routeState` (`object | undefined`): supports `prompt` prefill when entering the screen.
- `onNavigate` (`function | undefined`): callback used by assistant suggested actions.

## Child UI Units (in same file)

- `HistorySidebar`: list/select/delete conversation threads.
- `AssistantMessage`: markdown renderer for assistant output, with artifacts and suggested actions.
- `UserMessage`: user message bubble.
- `LoadingIndicator`: assistant progress state.
- `EmptyState`: starter prompts for first interaction.

## Data and API Flow

All requests use `API_BASE` from shared constants and include `Authorization` when `authToken` exists.

### Conversations
- `GET /api/conversations`
  - Loads sidebar history.
- `GET /api/conversations/:id`
  - Loads a selected thread.
- `DELETE /api/conversations/:id`
  - Deletes a thread.

### Chat
- `POST /api/chat`
  - Sends user message and optional `conversation_id`.
  - Expects assistant payload with:
    - `response` or `message.markdown`
    - `message.artifacts`
    - `message.datasets`
    - `message.suggested_actions`
    - `conversation_id`

## Interaction Model

- Enter sends message (Shift+Enter reserved for newline behavior patterns).
- Input disables while request is in flight.
- New conversation clears current messages and canvas state.
- Message list auto-scrolls to latest response.
- Suggestions in empty state can trigger immediate send.

## Voice Input

Uses shared `useVoiceInput` hook:
- Appends final speech transcript chunks into the current input.
- Mic toggle is shown only when browser speech recognition is supported.

## Artifact Canvas

When assistant response includes artifacts:
- “Open analysis” button appears on the assistant message.
- Right panel opens with `ArtifactCanvas`.
- Canvas receives `artifacts` and `datasets` from selected assistant message.

## Markdown Rendering

Assistant markdown is rendered with:
- `react-markdown`
- `remark-gfm`
- custom component map for paragraph/list/code styling

## Error Handling

- Conversation list/select/delete failures are intentionally non-blocking to keep UI usable.
- Chat failures append an assistant error-style message into the thread.

## Notes for Contributors

- Keep the assistant response object normalized before pushing to `messages` state.
- Preserve auth header forwarding for all assistant endpoints.
- If backend schema changes, update the assistant payload mapping first (`markdown`, `artifacts`, `datasets`, `suggested_actions`).
- Prefer resilient UI behavior over hard failures for non-critical endpoints (history, delete).
