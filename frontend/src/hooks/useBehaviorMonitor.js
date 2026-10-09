import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

const INTERVAL_MS = 1500 // one small frame every 1.5 s - never 30 fps

/**
 * Samples a downscaled webcam frame, sends it to the backend for LOCAL analysis (frame is not stored),
 * and reports tab visibility/focus changes. Only summarised observations come back.
 */
export function useBehaviorMonitor({ sessionId, videoRef, enabled, cameraOn }) {
  const [observation, setObservation] = useState(null)
  const [ratio, setRatio] = useState(null)
  const [events, setEvents] = useState(0)
  const busy = useRef(false)

  useEffect(() => {
    if (!enabled || !sessionId) return undefined
    const canvas = document.createElement('canvas')
    const controller = new AbortController()
    const timer = setInterval(async () => {
      const video = videoRef.current
      if (!cameraOn || busy.current || !video || video.readyState < 2 || !video.videoWidth) return
      busy.current = true
      try {
        const w = 320, h = Math.round((video.videoHeight / video.videoWidth) * w)
        canvas.width = w; canvas.height = h
        canvas.getContext('2d').drawImage(video, 0, 0, w, h)
        const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.6))
        if (blob) {
          const res = await api.analyzeFrame(sessionId, blob, controller.signal)
          setObservation(res.observation)
          setRatio(res.screen_attention_ratio)
          if (res.new_events?.length) setEvents((n) => n + res.new_events.length)
        }
      } catch { /* analysis is best-effort; never interrupt the interview */ } finally { busy.current = false }
    }, INTERVAL_MS)

    const onVisibility = () => { if (document.hidden) api.behaviorEvent(sessionId, 'tab_hidden').then(() => setEvents((n) => n + 1)).catch(() => {}) }
    const onBlur = () => { if (!document.hidden) api.behaviorEvent(sessionId, 'window_blur').then(() => setEvents((n) => n + 1)).catch(() => {}) }
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    return () => {
      clearInterval(timer); controller.abort()
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
    }
  }, [enabled, sessionId, videoRef, cameraOn])

  return { observation, ratio, events }
}
