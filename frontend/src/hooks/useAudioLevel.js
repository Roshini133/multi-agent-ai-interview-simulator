import { useEffect, useState } from 'react'

/** Returns a smoothed 0..1 microphone level for a MediaStream (used for the mic test / waveform). */
export function useAudioLevel(stream, active = true) {
  const [level, setLevel] = useState(0)
  useEffect(() => {
    if (!stream || !active || stream.getAudioTracks().length === 0) { setLevel(0); return undefined }
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return undefined
    const ctx = new Ctx()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    ctx.createMediaStreamSource(stream).connect(analyser)
    const data = new Uint8Array(analyser.frequencyBinCount)
    let raf
    const tick = () => {
      analyser.getByteTimeDomainData(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) { const v = (data[i] - 128) / 128; sum += v * v }
      setLevel((prev) => prev * 0.6 + Math.min(1, Math.sqrt(sum / data.length) * 5) * 0.4)
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => { cancelAnimationFrame(raf); ctx.close().catch(() => {}) }
  }, [stream, active])
  return level
}
