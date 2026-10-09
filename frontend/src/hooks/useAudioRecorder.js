import { useCallback, useRef, useState } from 'react'

/** Records the microphone track of a stream (audio only) so the backend can transcribe with Whisper. */
export function useAudioRecorder(stream) {
  const [recording, setRecording] = useState(false)
  const recRef = useRef(null)
  const chunks = useRef([])
  const startedAt = useRef(0)
  const resolver = useRef(null)

  const start = useCallback(() => {
    const audioTracks = stream?.getAudioTracks() || []
    if (!audioTracks.length || typeof MediaRecorder === 'undefined') return false
    try {
      const rec = new MediaRecorder(new MediaStream(audioTracks))
      chunks.current = []
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
      rec.onstop = () => {
        const blob = new Blob(chunks.current, { type: rec.mimeType || 'audio/webm' })
        resolver.current?.({ blob, seconds: (Date.now() - startedAt.current) / 1000 })
      }
      rec.start(500)
      startedAt.current = Date.now()
      recRef.current = rec
      setRecording(true)
      return true
    } catch { return false }
  }, [stream])

  const stop = useCallback(() => new Promise((resolve) => {
    if (!recRef.current || recRef.current.state === 'inactive') { setRecording(false); resolve(null); return }
    resolver.current = (r) => { setRecording(false); resolve(r) }
    recRef.current.stop()
  }), [])

  return { recording, start, stop }
}
