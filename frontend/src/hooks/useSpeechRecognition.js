import { useCallback, useEffect, useRef, useState } from 'react'

/** Browser speech recognition (Web Speech API) for live captions. Optional: falls back to typing. */
export function useSpeechRecognition() {
  const SR = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
  const [listening, setListening] = useState(false)
  const [finalText, setFinalText] = useState('')
  const [interim, setInterim] = useState('')
  const recRef = useRef(null)
  const wantRef = useRef(false)

  const start = useCallback(() => {
    if (!SR) return false
    const rec = new SR()
    rec.lang = 'en-US'
    rec.continuous = true
    rec.interimResults = true
    rec.onresult = (ev) => {
      let fin = '', tmp = ''
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const t = ev.results[i][0].transcript
        if (ev.results[i].isFinal) fin += t + ' '; else tmp += t
      }
      if (fin) setFinalText((p) => (p + fin).replace(/\s+/g, ' '))
      setInterim(tmp)
    }
    rec.onend = () => { setInterim(''); if (wantRef.current) { try { rec.start() } catch { setListening(false) } } else setListening(false) }
    rec.onerror = (e) => { if (e.error === 'not-allowed' || e.error === 'service-not-allowed') { wantRef.current = false; setListening(false) } }
    wantRef.current = true
    try { rec.start(); recRef.current = rec; setListening(true); return true } catch { return false }
  }, [SR])

  const stop = useCallback(() => { wantRef.current = false; recRef.current?.stop(); setListening(false) }, [])
  const reset = useCallback(() => { setFinalText(''); setInterim('') }, [])
  useEffect(() => () => { wantRef.current = false; recRef.current?.abort?.() }, [])
  return { supported: !!SR, listening, finalText, interim, start, stop, reset, setFinalText }
}
