import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Custom hook for browser speech-to-text via the Web Speech API.
 *
 * Returns { listening, transcript, supported, start, stop, toggle }
 *
 * `onResult(text)` is called with each final transcript segment so the
 * caller can append it to an input field.
 */
export default function useVoiceInput({ onResult, lang = 'en-US' } = {}) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const recRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    setSupported(true);

    const recognition = new SpeechRecognition();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const last = event.results[event.results.length - 1];
      if (last.isFinal) {
        const text = last[0].transcript.trim();
        if (text && onResult) onResult(text);
      }
    };

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        console.warn('SpeechRecognition error:', event.error);
      }
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recRef.current = recognition;

    return () => {
      try { recognition.abort(); } catch (_) { /* noop */ }
    };
  }, [lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = useCallback(() => {
    if (!recRef.current || listening) return;
    try {
      recRef.current.start();
      setListening(true);
    } catch (_) { /* already started */ }
  }, [listening]);

  const stop = useCallback(() => {
    if (!recRef.current) return;
    try {
      recRef.current.stop();
    } catch (_) { /* noop */ }
    setListening(false);
  }, []);

  const toggle = useCallback(() => {
    listening ? stop() : start();
  }, [listening, start, stop]);

  return { listening, supported, start, stop, toggle };
}
