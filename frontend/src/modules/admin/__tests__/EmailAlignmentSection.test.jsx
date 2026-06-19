/**
 * modules/admin/__tests__/EmailAlignmentSection.test.jsx
 * LAUNCH-OPS9 — Run Check button, clean result, flagged issues list,
 * Notify panel recipient selection (existing members + custom emails),
 * and drafted email preview.
 *
 * Moved from modules/settings/__tests__/ (Session AE, MERGE-1).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../api/membersApi.js', () => ({
  membersApi: {
    checkEmailAlignment: vi.fn(),
    listMembers: vi.fn(),
  },
}))

import { membersApi } from '../api/membersApi.js'
import EmailAlignmentSection from '../components/EmailAlignmentSection.jsx'

const STATION = { station_id: 1, name: 'Newberg Township Station 1' }
const getToken = vi.fn().mockResolvedValue('test-token')

const CLEAN_RESULT = { checked: 3, flagged: 0, issues: [] }

const FLAGGED_RESULT = {
  checked: 3,
  flagged: 1,
  issues: [
    {
      member_id: 7,
      station_id: 1,
      station_name: 'Newberg Township Station 1',
      user_id: 'Earl Jones',
      role: 'Supervisor',
      preferred_name: null,
      active: true,
      reason: 'contains a space -- looks like a display name, not an email',
    },
  ],
}

const MEMBERS = [
  { member_id: 1, user_id: 'jsmith@newbergtownship.org', preferred_name: 'Jennifer Smith', role: 'Administrator', active: true },
  { member_id: 2, user_id: 'mwilliams@newbergtownship.org', preferred_name: 'Mike Williams', role: 'Responder', active: true },
]

beforeEach(() => {
  vi.clearAllMocks()
})

describe('EmailAlignmentSection — running the check', () => {
  it('shows a Run Check button', () => {
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    expect(screen.getByRole('button', { name: /run check/i })).toBeTruthy()
  })

  it('calls checkEmailAlignment with the station id on click', async () => {
    const user = userEvent.setup()
    membersApi.checkEmailAlignment.mockResolvedValue(CLEAN_RESULT)
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await waitFor(() => expect(membersApi.checkEmailAlignment).toHaveBeenCalledWith(1, getToken))
  })

  it('shows a clean message when nothing is flagged', async () => {
    const user = userEvent.setup()
    membersApi.checkEmailAlignment.mockResolvedValue(CLEAN_RESULT)
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    expect(await screen.findByText(/all emails look good/i)).toBeTruthy()
  })

  it('shows an error message if the check fails', async () => {
    const user = userEvent.setup()
    membersApi.checkEmailAlignment.mockRejectedValue(new Error('Network error'))
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    expect(await screen.findByText(/network error/i)).toBeTruthy()
  })
})

describe('EmailAlignmentSection — flagged results', () => {
  beforeEach(() => {
    membersApi.checkEmailAlignment.mockResolvedValue(FLAGGED_RESULT)
  })

  it('lists the flagged entry with its reason', async () => {
    const user = userEvent.setup()
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    expect(await screen.findByText('"Earl Jones"')).toBeTruthy()
    expect(screen.getByText(/looks like a display name/i)).toBeTruthy()
  })

  it('shows the Notify Someone button', async () => {
    const user = userEvent.setup()
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    expect(await screen.findByRole('button', { name: /notify someone/i })).toBeTruthy()
  })

  it('opens the notify panel and loads candidate recipients', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue(MEMBERS)
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    expect(await screen.findByText(/jennifer smith/i)).toBeTruthy()
  })

  it('excludes the flagged person themselves from the recipient list', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue([
      ...MEMBERS,
      { member_id: 7, user_id: 'Earl Jones', preferred_name: null, role: 'Supervisor', active: true },
    ])
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    await screen.findByText(/jennifer smith/i)
    expect(screen.queryByText('Earl Jones')).toBeNull()
  })

  it('Draft Email is disabled until a recipient is chosen', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue(MEMBERS)
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    await screen.findByText(/jennifer smith/i)
    expect(screen.getByRole('button', { name: /draft email/i })).toBeDisabled()
  })

  it('selecting a recipient checkbox enables Draft Email', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue(MEMBERS)
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    const checkbox = await screen.findByLabelText(/jennifer smith/i, { exact: false })
    await user.click(checkbox)
    expect(screen.getByRole('button', { name: /draft email/i })).not.toBeDisabled()
  })

  it('adding a custom email enables Draft Email and shows the chip', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue([])
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    const input = screen.getByLabelText(/additional recipient email/i)
    await user.type(input, 'chief@newbergtownship.org')
    await user.click(screen.getByRole('button', { name: /^add$/i }))
    expect(await screen.findByText('chief@newbergtownship.org')).toBeTruthy()
    expect(screen.getByRole('button', { name: /draft email/i })).not.toBeDisabled()
  })

  it('clicking Draft Email shows a preview with recipients and body', async () => {
    const user = userEvent.setup()
    membersApi.listMembers.mockResolvedValue([])
    render(<EmailAlignmentSection station={STATION} getToken={getToken} />)
    await user.click(screen.getByRole('button', { name: /run check/i }))
    await user.click(await screen.findByRole('button', { name: /notify someone/i }))
    const input = screen.getByLabelText(/additional recipient email/i)
    await user.type(input, 'chief@newbergtownship.org')
    await user.click(screen.getByRole('button', { name: /^add$/i }))
    await user.click(screen.getByRole('button', { name: /draft email/i }))
    expect(await screen.findByText(/to: chief@newbergtownship.org/i)).toBeTruthy()
    expect(screen.getByText(/open in mail app/i)).toBeTruthy()
  })
})
