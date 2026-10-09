import { useEffect, useState } from 'react'

export function useTimer(initialSeconds = 0, running = true) {
  const [seconds, setSeconds] = useState(initialSeconds)
  useEffect(() => { setSeconds(initialSeconds) }, [initialSeconds])
  useEffect(() => {
    if (!running) return undefined
    const t = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [running])
  return seconds
}
