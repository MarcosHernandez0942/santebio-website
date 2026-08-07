import './App.css'
import Hero from './components/Hero.jsx'
import IntroVideo from './components/IntroVideo.jsx'

export default function App() {
  return (
    <IntroVideo src="/videos/intro_16x9.mp4" srcMobile="/videos/intro_9x16.mp4">
      <Hero />
    </IntroVideo>
  )
}
