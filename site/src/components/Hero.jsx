import VideoBackground from './VideoBackground.jsx'
import Reveal from './Reveal.jsx'

export default function Hero() {
  return (
    <section id="inicio" className="video-section">
      <VideoBackground src="/videos/escena1_nopal_16x9.mp4" srcMobile="/videos/escena1_nopal_9x16.mp4" />
      <div className="scrim scrim-bottom-left" />
      <div className="wrap section-content">
        <Reveal className="hero-body">
          <div className="eyebrow">100% Orgánico</div>
          <h1>Nopal en cápsulas, práctico para tu rutina</h1>
          <p className="subhead">
            Consulta ingredientes, presentación y forma de uso antes de comprar.
          </p>
          <div className="hero-ctas">
            <a className="btn btn-primary" href="#producto">Comprar ahora</a>
            <a className="btn btn-ghost" href="#faq">Resolver mis dudas</a>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
