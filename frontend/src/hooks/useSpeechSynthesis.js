import { useCallback, useEffect, useRef, useState } from 'react'

/** Text-to-speech for the AI interviewer (browser voices, no external service). */
export function useSpeechSynthesis(enabled = true) {
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [speaking, setSpeaking] = useState(false)
  const token = useRef(0)

  const cancel = useCallback(() => { if (supported) window.speechSynthesis.cancel(); setSpeaking(false) }, [supported])

  const speak = useCallback((text) => new Promise((resolve) => {
    if (!supported || !enabled || !text) { resolve(); return }
    window.speechSynthesis.cancel()
    const id = ++token.current
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 0.98
    const voices = window.speechSynthesis.getVoices()
    const v = voices.find((x) => /en[-_](US|GB|IN)/i.test(x.lang) && /female|zira|samantha|google/i.test(x.name)) || voices.find((x) => /^en/i.test(x.lang))
    if (v) u.voice = v
    u.onstart = () => setSpeaking(true)
    const done = () => { if (token.current === id) setSpeaking(false); resolve() }
    u.onend = done
    u.onerror = done
    window.speechSynthesis.speak(u)
  }), [supported, enabled])

  useEffect(() => () => { if (supported) window.speechSynthesis.cancel() }, [supported])
  return { supported, speaking, speak, cancel }
}
