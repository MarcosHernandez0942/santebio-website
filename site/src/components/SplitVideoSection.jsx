import VideoBackground from './VideoBackground.jsx'
import Reveal from './Reveal.jsx'

export default function SplitVideoSection({ id, videoSrc, videoSrcMobile, eyebrow, title, body, children }) {
  return (
    <section id={id} className="video-section align-right">
      <VideoBackground src={videoSrc} srcMobile={videoSrcMobile} />
      <div className="scrim scrim-right" />
      <div className="wrap section-content">
        <Reveal className="split-copy">
          <div className="eyebrow">{eyebrow}</div>
          <h2>{title}</h2>
          <p className="body">{body}</p>
          {children}
        </Reveal>
      </div>
    </section>
  )
}
