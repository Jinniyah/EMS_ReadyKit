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
    body: 'This app helps your crew check the truck every day so the right supplies are always on board when you need them.',
  },
  {
    icon: '✓',
    title: 'Check the Truck each day',
    body: 'Tap "Check the Truck" from the home screen and walk through each compartment. Count what you have — the app keeps track.',
  },
  {
    icon: '📋',
    title: 'Found a problem? Report it',
    body: 'If something is missing, expired, or broken, mark it. Your supervisor will be notified right away and nothing gets missed.',
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
