import { useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Camera, Mic, RefreshCw } from 'lucide-react'
import { ErrorAlert, Stepper } from '../components/ui'
import VideoPanel from '../components/VideoPanel'
import { useMediaStream } from '../hooks/useMediaStream'
import { useAudioLevel } from '../hooks/useAudioLevel'
import { STEPS } from './Setup'

export default function DeviceCheck() {
  const { id } = useParams()
  const nav = useNavigate()
  const ref = useRef(null)
  const media = useMediaStream()
  const level = useAudioLevel(media.stream, media.audioOn)
  const ok = !!media.stream

  return (
    <div className="container page" style={{ maxWidth: 900 }}>
      <Stepper steps={STEPS} current={2} />
      <h1 style={{ fontSize: '1.7rem' }}>Camera and microphone check</h1>
      <p className="muted">Make sure your face is centred and well lit, and that the microphone level moves when you speak.</p>
      <ErrorAlert error={media.error} />
      <div className="grid g2" style={{ margin: '16px 0', alignItems: 'start' }}>
        <VideoPanel ref={ref} stream={media.stream} videoOn={media.videoOn} />
        <div className="card stack">
          <div className="row"><Camera size={18} /><b>Camera</b><span className={`badge ${ok && media.videoOn ? 'good' : 'muted'}`}>{ok && media.videoOn ? 'Working' : 'Not detected'}</span></div>
          <div><div className="row"><Mic size={18} /><b>Microphone</b><span className={`badge ${ok && level > 0.04 ? 'good' : 'muted'}`}>{ok && level > 0.04 ? 'Hearing you' : 'Say something'}</span></div>
            <div className="meter" style={{ marginTop: 8 }} role="meter" aria-valuenow={Math.round(level * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Microphone level"><div style={{ width: `${Math.round(level * 100)}%` }} /></div></div>
          <ul className="bul small muted"><li>Sit in front of a light source, not with it behind you.</li><li>Keep your face inside the frame.</li><li>Use headphones to avoid echo if possible.</li></ul>
          <div className="row wrap">
            {!ok ? <button className="btn btn-primary" onClick={media.start}>Allow camera and microphone</button>
              : <><button className="btn btn-ghost btn-sm" onClick={media.toggleVideo}>{media.videoOn ? 'Turn camera off' : 'Turn camera on'}</button><button className="btn btn-ghost btn-sm" onClick={media.start}><RefreshCw size={14} /> Restart</button></>}
          </div>
        </div>
      </div>
      <div className="row wrap">
        <button className="btn btn-primary btn-lg" disabled={!ok} onClick={() => { media.stop(); nav(`/interview/${id}/lobby`) }}>Continue to lobby</button>
        <button className="btn btn-ghost" onClick={() => { media.stop(); nav(`/interview/${id}/lobby`) }}>Skip (text-only, no webcam)</button>
      </div>
    </div>
  )
}
