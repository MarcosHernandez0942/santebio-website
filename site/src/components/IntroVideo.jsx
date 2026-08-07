import { useEffect, useRef, useState } from 'react'
import useIsMobile from '../hooks/useIsMobile.js'
import './IntroVideo.css'

// Video de bienvenida a pantalla completa: se reproduce una sola vez al
// abrir la página y, al terminar (o si se salta), se desvanece y deja
// ver el contenido normal (ya montado detrás, sin parpadeo).
export default function IntroVideo({ src, srcMobile, children }) {
  const [fading, setFading] = useState(false)
  const [done, setDone] = useState(false)
  const videoRef = useRef(null)
  const isMobile = useIsMobile()
  const activeSrc = isMobile && srcMobile ? srcMobile : src

  useEffect(() => {
    document.body.style.overflow = done ? '' : 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [done])

  function finish() {
    if (fading || done) return
    setFading(true)
    setTimeout(() => setDone(true), 500) // debe coincidir con la transición en IntroVideo.css
  }

  return (
    <>
      {children}
      {!done && (
        <div className={`intro-overlay ${fading ? 'intro-fade-out' : ''}`}>
          <video
            ref={videoRef}
            src={activeSrc}
            autoPlay
            muted
            playsInline
            onEnded={finish}
            onError={finish}
          />
          <button type="button" className="intro-skip" onClick={finish}>
            Omitir intro
          </button>
        </div>
      )}
    </>
  )
}
