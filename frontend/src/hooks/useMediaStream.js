import { useCallback, useEffect, useRef, useState } from 'react'

const explain = (e) => {
  if (e?.name === 'NotAllowedError' || e?.name === 'SecurityError') return 'Camera/microphone permission was denied. Allow access in your browser address bar and try again.'
  if (e?.name === 'NotFoundError' || e?.name === 'OverconstrainedError') return 'No camera or microphone was found on this device.'
  if (e?.name === 'NotReadableError') return 'Your camera or microphone is being used by another application.'
  return 'Could not access the camera/microphone.'
}

/** Manages getUserMedia; exposes mute/camera toggles that never stop the underlying track. */
export function useMediaStream({ video = true, audio = true } = {}) {
  const [stream, setStream] = useState(null)
  const [error, setError] = useState(null)
  const [videoOn, setVideoOn] = useState(video)
  const [audioOn, setAudioOn] = useState(audio)
  const ref = useRef(null)

  const stop = useCallback(() => {
    ref.current?.getTracks().forEach((t) => t.stop())
    ref.current = null
    setStream(null)
  }, [])

  const start = useCallback(async () => {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Your browser does not support camera access (or the page is not served over HTTPS/localhost).')
      return null
    }
    try {
      stop()
      const s = await navigator.mediaDevices.getUserMedia({
        video: video ? { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' } : false,
        audio: audio ? { echoCancellation: true, noiseSuppression: true } : false,
      })
      ref.current = s
      setStream(s)
      setVideoOn(true); setAudioOn(true)
      return s
    } catch (e) {
      setError(explain(e))
      return null
    }
  }, [audio, video, stop])

  const toggleVideo = useCallback(() => {
    const track = ref.current?.getVideoTracks()[0]
    if (!track) return
    track.enabled = !track.enabled
    setVideoOn(track.enabled)
  }, [])
  const toggleAudio = useCallback(() => {
    const track = ref.current?.getAudioTracks()[0]
    if (!track) return
    track.enabled = !track.enabled
    setAudioOn(track.enabled)
  }, [])

  useEffect(() => stop, [stop])
  return { stream, error, videoOn, audioOn, start, stop, toggleVideo, toggleAudio }
}
