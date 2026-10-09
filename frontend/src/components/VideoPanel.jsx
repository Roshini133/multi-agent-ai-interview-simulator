import { forwardRef, useEffect } from 'react'
import { CameraOff } from 'lucide-react'

/** Mirrored self-view. The <video> is muted so the candidate never hears their own microphone. */
const VideoPanel = forwardRef(function VideoPanel({ stream, videoOn = true, children }, ref) {
  useEffect(() => {
    if (ref?.current) ref.current.srcObject = stream || null
  }, [stream, ref])
  return (
    <div className="video-box candidate-cam">
      <video ref={ref} autoPlay playsInline muted aria-label="Your camera preview" />
      {(!stream || !videoOn) && <div className="video-off"><div><CameraOff size={30} /><p>{stream ? 'Camera is off' : 'Camera not started'}</p></div></div>}
      {children}
    </div>
  )
})
export default VideoPanel
