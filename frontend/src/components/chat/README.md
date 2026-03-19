# Chat Components

Reusable chat UI primitives for Frammer AI Copilot interactions.

## Files

- `ChatPanel.jsx`: container shell, message state, API orchestration.
- `ChatMessage.jsx`: user/assistant message renderer with markdown + optional metadata blocks.
- `ChatInput.jsx`: text + voice input with suggestions and send controls.

## Architecture Overview

`ChatPanel` composes `ChatMessage` and `ChatInput` to provide a complete side-panel chat experience:

1. User enters text (or voice transcript) in `ChatInput`.
2. `ChatPanel` appends user message locally.
3. `ChatPanel` sends `POST /api/chat`.
4. Assistant reply is appended as an assistant message.
5. `ChatMessage` renders markdown and optional returned data blocks.

## Component Contracts

### `ChatPanel`

```jsx
<ChatPanel
  isOpen={isOpen}
  onClose={onClose}
  authToken={authToken}
  agentOk={agentOk}
  databaseOk={databaseOk}
/>
```

Props:
- `isOpen`: controls slide-in/out panel visibility.
- `onClose`: callback for close button.
- `authToken`: bearer token forwarded to chat API if available.
- `agentOk`: service health flag used for status pill + disable behavior.
- `databaseOk`: DB health flag displayed in status pill.

Internal behavior:
- Maintains `messages`, `input`, and `loading` state.
- Auto-scrolls to latest message.
- Prevents send when input is empty or request is in progress.
- If `agentOk === false`, shows offline assistant message instead of calling API.

API call:
- `POST /api/chat`
- Body: `{ message, filters: {} }`
- Expected fields from response:
  - `response`
  - optional `chart_data`
  - optional `actions`

### `ChatMessage`

```jsx
<ChatMessage msg={msg} showActivity={false} />
```

Props:
- `msg`: message object with `role`, `content`, and optional metadata.
- `showActivity` (optional): toggles display of activity steps for assistant messages.

Message rendering:
- User messages: right-aligned white bubble.
- Assistant messages: left-aligned dark bubble with markdown rendering.

Assistant metadata blocks:
- `chartData`: summarized as returned dataset names and row counts.
- `actions`: collapsible “Agent activity” list (when `showActivity` is true).

Markdown support:
- Uses `react-markdown` + `remark-gfm`.
- Supports headings, lists, tables, inline code, and fenced code blocks.

### `ChatInput`

```jsx
<ChatInput
  value={input}
  onChange={setInput}
  onSend={send}
  disabled={loading}
  placeholder="Ask Frammer AI anything..."
  suggestions={suggestions}
/>
```

Props:
- `value`: input text value.
- `onChange`: setter callback (string or updater function).
- `onSend`: send handler.
- `disabled` (optional): disables controls during request/offline state.
- `placeholder` (optional)
- `suggestions` (optional): clickable prompt chips.

Voice behavior:
- Integrates `useVoiceInput` hook.
- Appends recognized transcript chunks to existing input.
- Shows mic toggle only if speech recognition is supported.
- Enter sends message (Shift+Enter does not send).

## Message Object Shapes

### User message

```json
{
  "role": "user",
  "content": "Top 5 channels by uploads"
}
```

### Assistant message

```json
{
  "role": "assistant",
  "content": "Here is what I found...",
  "chartData": {
    "summary": [{ "metric": "uploaded_count", "value": 120 }]
  },
  "actions": ["Fetched overview", "Calculated trend"]
}
```

## Styling and UX Notes

- Dark mode chat panel with fixed right-side drawer layout.
- Header includes connection status badges for DB and agent health.
- Loading state displays pulsing assistant placeholder.
- Suggestions are lightweight quick-start chips for common prompts.

## Current Behavior Notes

- `ChatPanel` currently passes `showThinking` prop to `ChatMessage`, while `ChatMessage` uses `showActivity`.
- This mismatch means activity toggling is effectively off in current composition unless prop names are aligned.

## Dependencies

- `react-markdown`
- `remark-gfm`
- `lucide-react`
- shared hook: `useVoiceInput`
- shared config: `API_BASE`

## Extension Guidance

When extending chat behavior:

1. Keep API payload mapping inside `ChatPanel`.
2. Keep message presentation-only logic inside `ChatMessage`.
3. Keep input interaction logic inside `ChatInput`.
4. Preserve graceful offline/error states to avoid blocking user flow.
5. If adding new assistant metadata fields, render them as optional blocks in `ChatMessage`.

## Quick QA Checklist

- Panel opens/closes with smooth transition.
- Enter sends message; empty input does not send.
- Agent offline state disables input and prevents network request.
- Voice input appends transcript when supported.
- Markdown tables/lists/code render correctly.
- Returned chartData/action metadata appears without breaking message layout.
