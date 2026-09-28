import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { marked } from 'marked'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, STATUSES, type Application, type Status } from '../api'
import { ScoreBadge } from '../components/ScoreBadge'
import { printAsPdf } from '../lib/print'

type Tab = 'tailored_cv' | 'cover_letter'

export default function ApplicationPage() {
  const id = Number(useParams().id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: app, error, isPending } = useQuery({
    queryKey: ['applications', id],
    queryFn: () => api.getApplication(id),
  })
  const [tab, setTab] = useState<Tab>('tailored_cv')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const updateMutation = useMutation({
    mutationFn: (changes: Partial<Application>) => api.updateApplication(id, changes),
    onSuccess: (updated) => {
      queryClient.setQueryData(['applications', id], updated)
      queryClient.invalidateQueries({ queryKey: ['applications'], exact: true })
    },
  })
  const update = updateMutation.mutateAsync

  async function remove() {
    if (!confirm('Delete this application?')) return
    await api.deleteApplication(id)
    queryClient.invalidateQueries({ queryKey: ['applications'], exact: true })
    navigate('/')
  }

  if (isPending) return <p>Loading…</p>
  if (error) return <p className="text-rose-600">{error.message}</p>

  const matched = app.matches.filter((m) => m.matched)
  const missing = app.matches.filter((m) => !m.matched)
  const title = `${app.role} - ${app.company}`
  const document = app[tab]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{app.role || 'Untitled role'}</h1>
          <p className="text-slate-600">
            {app.company || 'Unknown company'}
            {app.job_url && (
              <> · <a href={app.job_url} target="_blank" rel="noreferrer" className="text-indigo-600 underline">job posting</a></>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ScoreBadge score={app.match_score} large />
          <select
            value={app.status}
            onChange={(e) => update({ status: e.target.value as Status })}
            className="rounded-md border border-slate-300 px-2 py-1.5"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <button onClick={remove} className="text-sm text-rose-600 hover:underline">Delete</button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        {/* Requirements */}
        <aside className="space-y-4">
          <RequirementList title={`You have (${matched.length})`} items={matched} ok />
          <RequirementList title={`Gaps (${missing.length})`} items={missing} ok={false} />
          <div>
            <h2 className="mb-1 font-semibold">Notes</h2>
            <textarea
              defaultValue={app.notes}
              onBlur={(e) => e.target.value !== app.notes && update({ notes: e.target.value })}
              rows={4}
              placeholder="Recruiter name, interview dates… (saves when you click away)"
              className="w-full rounded-md border border-slate-300 p-2 text-sm"
            />
          </div>
        </aside>

        {/* Tailored documents */}
        <section className="rounded-lg border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 p-3">
            {(['tailored_cv', 'cover_letter'] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setEditing(false) }}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${tab === t ? 'bg-slate-800 text-white' : 'bg-slate-100'}`}
              >
                {t === 'tailored_cv' ? 'Tailored CV' : 'Cover letter'}
              </button>
            ))}
            <div className="ml-auto flex gap-2">
              {editing ? (
                <>
                  <button onClick={() => setEditing(false)} className="rounded-md px-3 py-1.5 text-sm">Cancel</button>
                  <button
                    onClick={async () => { await update({ [tab]: draft }); setEditing(false) }}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white"
                  >
                    Save
                  </button>
                </>
              ) : (
                <>
                  <button onClick={() => { setDraft(document); setEditing(true) }} className="rounded-md bg-slate-100 px-3 py-1.5 text-sm">Edit</button>
                  <button onClick={() => navigator.clipboard.writeText(document)} className="rounded-md bg-slate-100 px-3 py-1.5 text-sm">Copy</button>
                  <button
                    onClick={() => printAsPdf(`${tab === 'tailored_cv' ? 'CV' : 'Cover letter'} - ${title}`, document)}
                    className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm text-white"
                  >
                    Download PDF
                  </button>
                </>
              )}
            </div>
          </div>
          {editing ? (
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={28}
              className="w-full p-4 font-mono text-sm outline-none"
            />
          ) : (
            <div
              className="markdown p-6"
              dangerouslySetInnerHTML={{ __html: marked.parse(document, { breaks: true }) as string }}
            />
          )}
        </section>
      </div>
    </div>
  )
}

function RequirementList({ title, items, ok }: { title: string; items: Application['matches']; ok: boolean }) {
  return (
    <div>
      <h2 className="mb-2 font-semibold">{title}</h2>
      <ul className="space-y-2">
        {items.map((m) => (
          <li key={m.skill} className={`rounded-md border-l-4 bg-white p-2 text-sm ${ok ? 'border-emerald-500' : 'border-rose-400'}`}>
            <p className="font-medium">
              {m.skill}
              {m.importance === 'must' && <span className="ml-1 text-xs text-slate-400">required</span>}
            </p>
            <p className="text-slate-600">{m.note}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
