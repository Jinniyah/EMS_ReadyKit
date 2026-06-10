/**
 * shared/components/Tutorial.jsx
 * First-run tutorial overlay — 3 slides shown once on first login.
 * Dismissed by tapping Next/Done or Skip.
 * Flag stored in localStorage under 'ems_tutorial_complete'.
 */
import React, { useState } from 'react'

const TUTORIAL_KEY = 'ems_tutorial_complete'

const SLIDES = [
  {
    icon: '🚑',
    title: 'Welcome to EMS ReadyKit',
    body: 'Two big buttons on the home screen: "Check the Truck" for your daily walk-through, and "Log Items Used" after a call. That\'s it.',
  },
  {
    icon: '✓',
    title: 'Check the Truck — every shift',
    body: 'Tap the big green "Check the Truck" button. Walk each compartment, count what\'s there, and tap No Change or enter the new count. Submit when done.',
  },
  {
    icon: '📋',
    title: 'After a call — Log Items Used',
    body: 'Tap "Log Items Used." Pick what you used with the + button. Tap Done. The supply room counts update automatically — nothing to restock manually.',
  },
]

export function isTutorialComplete() {
  try { return !!localStorage.getItem(TUTORIAL_KEY) } catch { return true }
}

function markComplete() {
  try { localStorage.setItem(TUTORIAL_KEY, '1') } catch { /* ignore */ }
}

export default function Tutorial({ onDone }) {
  const [slide, setSlide] = useState(0)

  function handleNext() {
    if (slide < SLIDES.length - 1) {
      setSlide(s => s + 1)
    } else {
      markComplete()
      onDone()
    }
  }

  function handleSkip() {
    markComplete()
    onDone()
  }

  const { icon, title, body } = SLIDES[slide]
  const isLast = slide === SLIDES.length - 1

  return (
    <div className="tutorial-overlay" role="dialog" aria-modal="true" aria-label="Welcome tutorial">
      <div className="tutorial-slide" key={slide}>
        <div className="tutorial-slide__icon" aria-hidden="true">{icon}</div>
        <h1 className="tutorial-slide__title">{title}</h1>
        <p className="tutorial-slide__body">{body}</p>
        <div className="tutorial-dots" aria-hidden="true">
          {SLIDES.map((_, i) => (
            <div key={i} className={`tutorial-dot ${i === slide ? 'tutorial-dot--active' : ''}`} />
          ))}
        </div>
        <button className="tutorial-slide__btn" onClick={handleNext} type="button">
          {isLast ? 'Get started' : 'Next →'}
        </button>
        {!isLast && (
          <button className="tutorial-skip" onClick={handleSkip} type="button">
            Skip
          </button>
        )}
      </div>
    </div>
  )
}
