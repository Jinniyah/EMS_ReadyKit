import React, { useState } from 'react'
import { canAccess } from '../../shared/utils/roleGuard.js'
import Tutorial from '../../shared/components/Tutorial.jsx'
import './help.css'

function HelpAccordion({ title, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="help-accordion">
      <button
        className="help-accordion__trigger"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        type="button"
      >
        {title}
        <span className="help-accordion__chevron" aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="help-accordion__body">
          {children}
        </div>
      )}
    </div>
  )
}

function QuickItem({ icon, label, desc }) {
  return (
    <div className="help-quick-item">
      <span className="help-quick-item__icon" aria-hidden="true">{icon}</span>
      <div>
        <div className="help-quick-item__label">{label}</div>
        <div className="help-quick-item__desc">{desc}</div>
      </div>
    </div>
  )
}

export default function HelpScreen({ onBack, user }) {
  const [showTutorial, setShowTutorial] = useState(false)
  const isSupervisorPlus = canAccess(user, 'supervisor')

  return (
    <div className="help-screen">
      {showTutorial && (
        <Tutorial onDone={() => setShowTutorial(false)} />
      )}

      <div className="help-screen__header">
        <button className="btn-text" onClick={onBack} type="button">
          ← Back
        </button>
        <button
          className="btn btn--secondary"
          onClick={() => setShowTutorial(true)}
          type="button"
        >
          Replay Tutorial
        </button>
      </div>

      <h1 className="help-screen__title">Help &amp; Tutorial</h1>

      <section className="help-screen__section">
        <h2 className="help-screen__section-title">For Every Crew Member</h2>

        <HelpAccordion title="How to do your shift-start check">
          <ol>
            <li>Tap <strong>Check the Truck</strong> on the home screen.</li>
            <li>Pick your vehicle from the list.</li>
            <li>Walk through each compartment. Count what's there and tap the count, or tap <strong>No Change</strong> if nothing has moved.</li>
            <li>When you're done with all compartments, tap <strong>Submit</strong>.</li>
          </ol>
          <p>Your progress is saved automatically after each compartment. If you get interrupted, you can pick up where you left off.</p>
        </HelpAccordion>

        <HelpAccordion title="After a call — logging what you used">
          <ol>
            <li>Tap <strong>Log Items Used</strong> on the home screen.</li>
            <li>Tap <strong>+</strong> next to each item you used. The number counts up.</li>
            <li>Tap <strong>Done</strong> when finished.</li>
          </ol>
          <p>The supply room counts update automatically. You don't need to do anything else.</p>
        </HelpAccordion>

        <HelpAccordion title="What the colors mean">
          <ul>
            <li><strong>Green (PASS)</strong> — everything looks good for that check.</li>
            <li><strong>Red (FAIL)</strong> — something was missing, expired, or a reading was out of range. Action required.</li>
            <li><strong>Amber (NEEDS RESTOCK)</strong> — supplies are running low but not empty yet.</li>
          </ul>
        </HelpAccordion>

        <HelpAccordion title="What happens if you miss a check">
          <p>The truck will show as "Not checked today" on the supervisor's screen. If this happens, do the check as soon as you can. The system records when the check was submitted.</p>
        </HelpAccordion>

        <HelpAccordion title="An item is missing or expired">
          <p>Enter what you found — even if the count is zero. The system flags it automatically. A supervisor will see it.</p>
          <p>Do not skip the item or tap <strong>No Change</strong> if the item is actually missing or expired. That would hide the problem.</p>
        </HelpAccordion>

        <HelpAccordion title="A truck needs repair">
          <ol>
            <li>Tap <strong>Vehicle &amp; Equipment Status</strong> from the home screen.</li>
            <li>Find the vehicle and tap <strong>Report a Repair</strong>.</li>
            <li>Describe the problem and pick the urgency.</li>
            <li>Tap <strong>Submit</strong>. The supervisor is notified.</li>
          </ol>
        </HelpAccordion>

        <HelpAccordion title="You started a check and got a call">
          <p>Your progress is saved automatically after each compartment. When you return, tap <strong>Resume</strong> on the yellow banner at the top of the home screen. You'll pick up exactly where you left off.</p>
        </HelpAccordion>
      </section>

      {isSupervisorPlus && (
        <section className="help-screen__section">
          <h2 className="help-screen__section-title">For Supervisors</h2>

          <HelpAccordion title="How to see if all trucks were checked today">
            <ol>
              <li>Tap <strong>Compliance Dashboard</strong> on the home screen.</li>
              <li>You'll see a card for each vehicle. Green = checked and passed. Red = checked and failed. Grey = not checked yet.</li>
              <li>Tap any card to see the full details of that check.</li>
            </ol>
          </HelpAccordion>

          <HelpAccordion title="What a FAIL check means and what to do">
            <p>A FAIL means something was missing, expired, or a reading was out of range. The check is a permanent record — you cannot delete it.</p>
            <ol>
              <li>Tap the check in the Compliance Dashboard to open it.</li>
              <li>Review what failed.</li>
              <li>Once the issue is resolved, tap <strong>Acknowledge</strong> and add a note about what was done.</li>
            </ol>
          </HelpAccordion>

          <HelpAccordion title="How to add a crew member">
            <ol>
              <li>Tap <strong>Station Administration</strong> on the home screen.</li>
              <li>Tap <strong>Members</strong>.</li>
              <li>Tap <strong>Add Member</strong>. Enter their name and the email address they use to sign in.</li>
              <li>Pick their role (Responder or Supervisor) and tap <strong>Save</strong>.</li>
            </ol>
          </HelpAccordion>

          <HelpAccordion title="How to check supply room stock">
            <ol>
              <li>Tap <strong>Station Supplies</strong> on the home screen.</li>
              <li>Tap <strong>View Supplies</strong> to see current counts.</li>
              <li>If counts are wrong, tap <strong>Count Supplies</strong> to run a full recount.</li>
              <li>To record a new shipment, tap <strong>Receive Stock</strong>.</li>
            </ol>
          </HelpAccordion>
        </section>
      )}

      <section className="help-screen__section">
        <h2 className="help-screen__section-title">Quick Reference</h2>
        <p className="help-section-hint">What each button on the home screen does</p>
        <div className="help-quick-grid">
          <QuickItem icon="✓" label="Check the Truck" desc="Start a shift-start check on a vehicle" />
          <QuickItem icon="📋" label="Log Items Used" desc="Record supplies used after a call" />
          <QuickItem icon="🚑" label="Vehicle & Equipment Status" desc="Report repairs, mark out of service" />
          <QuickItem icon="📋" label="Check History" desc="See past checks you've submitted" />
          <QuickItem icon="🏪" label="Station Supplies" desc="View and manage supply room stock" />
          {isSupervisorPlus && (
            <QuickItem icon="📊" label="Compliance Dashboard" desc="Today's check status for all vehicles" />
          )}
          {isSupervisorPlus && (
            <QuickItem icon="👥" label="Station Administration" desc="Manage members, vehicles, and items" />
          )}
          {isSupervisorPlus && (
            <QuickItem icon="⚙️" label="Settings" desc="Station configuration and preferences" />
          )}
        </div>
      </section>

      <section className="help-screen__section">
        <h2 className="help-screen__section-title">Replay Tutorial</h2>
        <button
          className="help-replay-btn"
          onClick={() => setShowTutorial(true)}
          type="button"
        >
          Show me the basics again
        </button>
      </section>
    </div>
  )
}
