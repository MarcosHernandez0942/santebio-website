import { useEffect, useRef, useState } from 'react'
import useIsMobile from '../hooks/useIsMobile.js'

// srcMobile es opcional (el clip 9:16 de esa escena). Si todavía no
// existe ese archivo, el <video> dispara onError y se cae de vuelta al
// video de escritorio automáticamente — no rompe nada en lo que se
// suben los clips verticales.
export default function VideoBackground({ src, srcMobile }) {
  const [ready, setReady] = useState(false)
  const [mobileFailed, setMobileFailed] = useState(false)
  const isMobile = useIsMobile()
  const videoRef = useRef(null)

  const wantsMobile = isMobile && !!srcMobile && !mobileFailed
  const activeSrc = wantsMobile ? srcMobile : src

  useEffect(() => {
    setReady(false)
    const el = videoRef.current
    if (!el) return
    el.load()
    // autoplay solo se respeta en el montaje inicial — tras un load()
    // manual (ej. al caer de vuelta al video de escritorio) hay que
    // pedir play() explícitamente para que no quede pausado.
    const playPromise = el.play()
    if (playPromise) playPromise.catch(() => {})
  }, [activeSrc])

  return (
    <>
      <video
        ref={videoRef}
        src={activeSrc}
        autoPlay
        muted
        loop
        playsInline
        onLoadedData={() => setReady(true)}
        onError={() => {
          if (wantsMobile) setMobileFailed(true)
        }}
        className={ready ? 'video-ready' : ''}
      />
      <div className="scrim vignette" />
    </>
  )
}
