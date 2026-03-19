# hooks

Reusable React hooks for data fetching and voice input.

## Files

### `useApi.js`
Fetch helper hook for GET requests with built-in auth token handling.

```js
import { useApi } from './useApi';

const { data, loading, error, dataUrl } = useApi('/api/overview', []);
```

#### Signature
```js
useApi(url, dependencies = [])
```

#### Params
- `url` (`string | null | undefined`): request URL.
- `dependencies` (`Array`): dependency array forwarded to `useEffect`.

#### Returns
- `data`: parsed JSON response body, or `null` before success.
- `loading`: `true` while request is in flight.
- `error`: error message string when request fails.
- `dataUrl`: last successful URL used to set `data`.

#### Behavior notes
- Reads `frammer_auth_token` from `localStorage` and sends `Authorization: Bearer <token>` when available.
- On `401`, clears auth keys from `localStorage`:
  - `frammer_auth_token`
  - `frammer_auth_user`
- Ignores stale async updates on unmount.
- If `url` is falsy, skips request and sets `loading` to `false`.

### `useVoiceInput.js`
Speech-to-text hook built on the browser Web Speech API.

```js
import useVoiceInput from './useVoiceInput';

const { listening, supported, start, stop, toggle } = useVoiceInput({
  lang: 'en-US',
  onResult: (text) => {
    // append recognized text to input
    setMessage((prev) => `${prev} ${text}`.trim());
  },
});
```

#### Signature
```js
useVoiceInput({ onResult, lang = 'en-US' } = {})
```

#### Params
- `onResult` (`(text: string) => void`): called for each final transcript segment.
- `lang` (`string`): recognition locale, defaults to `en-US`.

#### Returns
- `listening`: whether recognition is currently active.
- `supported`: whether browser speech recognition is available.
- `start()`: starts recognition if possible.
- `stop()`: stops recognition.
- `toggle()`: convenience start/stop toggle.

#### Behavior notes
- Uses `window.SpeechRecognition` or `window.webkitSpeechRecognition`.
- Configured as `continuous = true` and `interimResults = false`.
- Handles non-abort errors by logging a warning and resetting listening state.
- Aborts recognition during cleanup to avoid leaks.

## Conventions
- Keep hooks focused on one concern each.
- Return small, predictable state/action objects.
- Add browser capability guards for Web APIs.
- Document side effects (network, localStorage, media/microphone) in the hook file and this README.
