
import { useEffect, useState } from 'react'
import './App.css'

const API = '/api'

const initialForm = {
  customer: '',
  subject: '',
  description: '',
}

function App() {
  const [page, setPage] = useState('dashboard')
  const [tickets, setTickets] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [analyses, setAnalyses] = useState([])
  const [result, setResult] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  async function apiRequest(path, options = {}) {
    const response = await fetch(`${API}${path}`, options)

    if (!response.ok) {
      let message = `Request failed (${response.status})`
      try {
        const data = await response.json()
        message = data.detail || message
      } catch {
        // Keep the HTTP status error
      }
      throw new Error(
        typeof message === 'string' ? message : JSON.stringify(message)
      )
    }

    return response.json()
  }

  async function loadTickets() {
    try {
      setError('')
      const data = await apiRequest('/tickets')
      setTickets(data)
      setSelectedId(current =>
        data.some(ticket => ticket.id === current)
          ? current
          : (data[0]?.id ?? null)
      )
    } catch (err) {
      setError(`Could not load tickets: ${err.message}`)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [])

  useEffect(() => {
    if (selectedId === null) {
      setAnalyses([])
      return
    }

    let cancelled = false

    apiRequest(`/tickets/${selectedId}/analyses`)
      .then(data => {
        if (!cancelled) setAnalyses(data)
      })
      .catch(err => {
        if (!cancelled) setError(err.message)
      })

    return () => {
      cancelled = true
    }
  }, [selectedId])

  const selectedTicket = tickets.find(
    ticket => ticket.id === selectedId
  )

  async function createTicket(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')

    try {
      const created = await apiRequest('/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })

      setForm(initialForm)
      await loadTickets()
      setSelectedId(created.id)
      setResult(null)
      setNotice(`Ticket #${created.id} created successfully.`)
      setPage('tickets')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function runInvestigation() {
    if (!selectedTicket) return

    setLoading(true)
    setError('')
    setNotice('')
    setResult(null)

    try {
      const data = await apiRequest(
        `/tickets/${selectedTicket.id}/full-investigation`,
        { method: 'POST' }
      )

      setResult(data)
      const history = await apiRequest(
        `/tickets/${selectedTicket.id}/analyses`
      )
      setAnalyses(history)
      setNotice('AI investigation completed.')
    } catch (err) {
      setError(`Investigation failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  function chooseTicket(ticketId) {
    setSelectedId(ticketId)
    setResult(null)
    setNotice('')
    setPage('investigation')
  }

  const openTickets = tickets.filter(
    ticket => ticket.status === 'open'
  ).length

const filteredTickets = tickets.filter(ticket => {
  const searchText = searchQuery.trim().toLowerCase()

  const matchesSearch = [
    ticket.id,
    ticket.subject,
    ticket.customer,
    ticket.description,
  ].some(value =>
    String(value ?? '').toLowerCase().includes(searchText)
  )

  const matchesStatus =
    statusFilter === 'all' ||
    ticket.status === statusFilter

  return matchesSearch && matchesStatus
})


  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <div>
            <strong>SupportAI</strong>
            <small>ENGINEER PLATFORM</small>
          </div>
        </div>

        <div className="nav-heading">WORKSPACE</div>

        <nav className="navigation">
          <button
            className={page === 'dashboard' ? 'active' : ''}
            onClick={() => setPage('dashboard')}
          >
            <span>▦</span> Dashboard
          </button>
          <button
            className={page === 'tickets' ? 'active' : ''}
            onClick={() => setPage('tickets')}
          >
            <span>▤</span> Tickets
          </button>
          <button
            className={page === 'investigation' ? 'active' : ''}
            onClick={() => setPage('investigation')}
          >
            <span>✧</span> AI Investigation
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="system-dot" />
          <div>
            <strong>Local workspace</strong>
            <small>FastAPI + Gemini</small>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">Workspace / {page}</div>
          <div className="topbar-right">
            <span className="environment">● Development</span>
            <div className="avatar">AI</div>
          </div>
        </header>

        <div className="content">
          {error && (
            <div className="alert error" role="alert">{error}</div>
          )}
          {notice && (
            <div className="alert success">{notice}</div>
          )}

          {page === 'dashboard' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">OVERVIEW</div>
                  <h1>Support Dashboard</h1>
                  <p>Monitor customer issues and AI investigations.</p>
                </div>
                <button
                  className="primary-button"
                  onClick={() => setPage('tickets')}
                >
                  + New ticket
                </button>
              </div>

              <div className="stats-grid">
                <StatCard label="Total Tickets" value={tickets.length} icon="▤" />
                <StatCard label="Open Tickets" value={openTickets} icon="◷" />
                <StatCard
                  label="Selected Ticket Analyses"
                  value={analyses.length}
                  icon="✧"
                />
              </div>

              <div className="section-heading">
                <div>
                  <h2>Recent tickets</h2>
                  <p>Customer requests from your SQLite database</p>
                </div>
                <button className="text-button" onClick={loadTickets}>
                  ↻ Refresh
                </button>
              </div>

              <TicketTable
                tickets={tickets.slice().reverse().slice(0, 8)}
                onSelect={chooseTicket}
              />
            </>
          )}

          {page === 'tickets' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">CUSTOMER SUPPORT</div>
                  <h1>Ticket Management</h1>
                  <p>Create and manage customer support requests.</p>
                </div>
              </div>

              <div className="two-column">
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Create a ticket</h2>
                    <p>Submit a new support request</p>
                  </div>

                  <form onSubmit={createTicket} className="ticket-form">
                    <label>
                      Customer name
                      <input
                        required
                        value={form.customer}
                        onChange={event => setForm({
                          ...form,
                          customer: event.target.value,
                        })}
                        placeholder="Example Company"
                      />
                    </label>

                    <label>
                      Subject
                      <input
                        required
                        value={form.subject}
                        onChange={event => setForm({
                          ...form,
                          subject: event.target.value,
                        })}
                        placeholder="Login Error"
                      />
                    </label>

                    <label>
                      Description
                      <textarea
                        required
                        rows={5}
                        value={form.description}
                        onChange={event => setForm({
                          ...form,
                          description: event.target.value,
                        })}
                        placeholder="Describe the issue..."
                      />
                    </label>

                    <button
                      className="primary-button"
                      type="submit"
                      disabled={saving}
                    >
                      {saving ? 'Creating...' : '+ Create ticket'}
                    </button>
                  </form>
                </section>

                <section className="panel">
                  <div className="panel-heading">
                    <h2>How it works</h2>
                    <p>Your AI-powered support workflow</p>
                  </div>

                  <div className="workflow-step">
                    <b>01</b>
                    <div>
                      <strong>Create a ticket</strong>
                      <p>Store the customer issue in SQLite.</p>
                    </div>
                  </div>
                  <div className="workflow-step">
                    <b>02</b>
                    <div>
                      <strong>Retrieve knowledge</strong>
                      <p>Find related technical documentation.</p>
                    </div>
                  </div>
                  <div className="workflow-step">
                    <b>03</b>
                    <div>
                      <strong>Investigate logs</strong>
                      <p>Gemini calls read-only log search tools.</p>
                    </div>
                  </div>
                  <div className="workflow-step">
                    <b>04</b>
                    <div>
                      <strong>Review findings</strong>
                      <p>Inspect AI analysis and suggested actions.</p>
                    </div>
                  </div>
                </section>
              </div>

              
<div className="section-heading">
  <div>
    <h2>All tickets</h2>
    <p>{filteredTickets.length} tickets found</p>
  </div>
  <button className="text-button" onClick={loadTickets}>
    ↻ Refresh
  </button>
</div>

<div className="ticket-filters">
  <input
    type="search"
    placeholder="Search by ticket, customer or description..."
    value={searchQuery}
    onChange={event => setSearchQuery(event.target.value)}
  />

  <select
    value={statusFilter}
    onChange={event => setStatusFilter(event.target.value)}
  >
    <option value="all">All statuses</option>
    <option value="open">Open</option>
    <option value="closed">Closed</option>
  </select>
</div>

<TicketTable
  tickets={filteredTickets}
  onSelect={chooseTicket}
/>

            </>
          )}

          {page === 'investigation' && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">AI WORKSPACE</div>
                  <h1>AI Investigation</h1>
                  <p>Analyze tickets using Gemini, RAG and log tools.</p>
                </div>
              </div>

              <section className="panel investigation-panel">
                <div className="panel-heading">
                  <h2>Select a support ticket</h2>
                  <p>Choose an existing ticket from SQLite</p>
                </div>

                <select
                  value={selectedId ?? ''}
                  onChange={event => {
                    setSelectedId(Number(event.target.value))
                    setResult(null)
                  }}
                  disabled={tickets.length === 0}
                >
                  {tickets.length === 0 && (
                    <option value="">No tickets available</option>
                  )}
                  {tickets.map(ticket => (
                    <option key={ticket.id} value={ticket.id}>
                      #{ticket.id} — {ticket.subject}
                    </option>
                  ))}
                </select>

                {selectedTicket && (
                  <div className="ticket-preview">
                    <div className="ticket-preview-top">
                      <strong>{selectedTicket.subject}</strong>
                      <span className="status-badge">
                        {selectedTicket.status}
                      </span>
                    </div>
                    <p>{selectedTicket.description}</p>
                    <small>Customer: {selectedTicket.customer}</small>
                  </div>
                )}

  
<button
  className="primary-button investigate-button"
  disabled={loading || !selectedTicket}
  onClick={runInvestigation}
>
  {loading ? (
    <>
      <span className="spinner" />
      Analyzing ticket...
    </>
  ) : (
    <>✧ Run AI Investigation</>
  )}
</button>

{loading && (
  <div className="investigation-progress" role="status">
    <div className="progress-indicator" />
    <div>
      <strong>AI investigation in progress</strong>
      <p>Retrieving documentation and investigating simulated logs...</p>
    </div>
  </div>
)}

{error && !loading && selectedTicket && (
  <div className="retry-panel">
    <div>
      <strong>Investigation could not be completed</strong>
      <p>You can retry the investigation.</p>
    </div>

    <button
      type="button"
      className="retry-button"
      onClick={runInvestigation}
    >
      ↻ Retry
    </button>
  </div>
)}


                <p className="helper-text">
                  Runs Gemini API requests. Log data is simulated.
                </p>
              </section>

              {result && (
                <div className="results-grid">
                  <section className="panel">
                    <div className="panel-heading">
                      <h2>AI Analysis</h2>
                      <p>Analysis #{result.analysis_id}</p>
                    </div>

                    <div className="result-field">
                      <small>CATEGORY</small>
                      <strong>{result.analysis.category}</strong>
                    </div>

                    <div className="result-field">
                      <small>PRIORITY</small>
                      <span
                                                            className={`priority-badge priority-${result.analysis.priority.toLowerCase()}`}
                                                       >
                                                            {result.analysis.priority}
                                                      </span>
                    </div>

                    <div className="result-field">
                      <small>POSSIBLE CAUSE</small>
                      <p>{result.analysis.possible_cause}</p>
                    </div>

                    <div className="result-field">
                      <small>SUGGESTED ACTION</small>
                      <p>{result.analysis.suggested_action}</p>
                    </div>

                    <div className="result-field">
                      <small>RETRIEVED DOCUMENTS</small>
                      {(result.analysis.sources || []).length ? (
                        result.analysis.sources.map(source => (
                          <div className="source-chip" key={source}>
                            ◈ {source}
                          </div>
                        ))
                      ) : (
                        <p>No matching documents.</p>
                      )}
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-heading">
                      <h2>Log Investigation</h2>
                      <p>Gemini tool calling findings</p>
                    </div>

                    <div className="log-output">
                      {result.log_investigation}
                    </div>
                    <p className="helper-text">
                      AI output is advisory. Verify findings before
                      taking operational action.
                    </p>
                  </section>
                </div>
              )}

              <section className="panel history-panel">
                <div className="panel-heading">
                  <h2>Analysis history</h2>
                  <p>Saved analyses for the selected ticket</p>
                </div>

                {analyses.length === 0 ? (
                  <div className="empty-state">
                    No saved analyses for this ticket.
                  </div>
                ) : (
                  analyses.map(item => (
                    <div className="history-row" key={item.id}>
                      <div>
                        <strong>Analysis #{item.id}</strong>
                        <p>{item.category} · {item.priority}</p>
                      </div>
                      <small>
                        {new Date(item.analyzed_at).toLocaleString()}
                      </small>
                    </div>
                  ))
                )}
              </section>
            </>
          )}

          <footer className="footer">
            SupportAI · AI Support Engineer · Local Development
          </footer>
        </div>
      </main>
    </div>
  )
}

function StatCard({ label, value, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span>{label}</span>
        <div className="stat-icon">{icon}</div>
      </div>
      <strong>{value}</strong>
      <small>Live application data</small>
    </div>
  )
}

function TicketTable({ tickets, onSelect }) {
  return (
    <div className="table-panel">
      {tickets.length === 0 ? (
        <div className="empty-state">
          No tickets yet. Create your first ticket to get started.
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>TICKET</th>
                <th>CUSTOMER</th>
                <th>STATUS</th>
                <th>CREATED</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tickets.map(ticket => (
                <tr key={ticket.id}>
                  <td>
                    <strong>{ticket.subject}</strong>
                    <small>#{ticket.id}</small>
                  </td>
                  <td>{ticket.customer}</td>
                  <td>
                    <span className="status-badge">
                      {ticket.status}
                    </span>
                  </td>
                  <td>
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      className="row-action"
                      onClick={() => onSelect(ticket.id)}
                    >
                      Investigate →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default App
