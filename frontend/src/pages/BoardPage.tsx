import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api, STATUSES, type Status } from '../api'
import { ScoreBadge } from '../components/ScoreBadge'

const LABELS: Record<Status, string> = {
  saved: 'Saved',
  applied: 'Applied',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
}

export default function BoardPage() {
  const queryClient = useQueryClient()
  const { data: applications, error, isPending } = useQuery({
    queryKey: ['applications'],
    queryFn: api.listApplications,
  })
  const move = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Status }) => api.updateApplication(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }),
  })

  if (isPending) return <p>Loading…</p>
  if (error) return <p className="text-rose-600">{error.message}</p>

  if (!applications.length) {
    return (
      <div className="py-16 text-center">
        <h1 className="text-2xl font-bold">No applications yet</h1>
        <p className="mt-2 text-slate-600">
          Start by <Link to="/profile" className="text-indigo-600 underline">adding your CV</Link>, then{' '}
          <Link to="/new" className="text-indigo-600 underline">analyze your first job</Link>.
        </p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-5">
      {STATUSES.map((status) => {
        const column = applications.filter((a) => a.status === status)
        return (
          <section key={status} className="rounded-lg bg-slate-100 p-3">
            <h2 className="mb-3 text-sm font-semibold text-slate-600">
              {LABELS[status]} <span className="text-slate-400">({column.length})</span>
            </h2>
            <div className="space-y-3">
              {column.map((app) => (
                <article key={app.id} className="rounded-md bg-white p-3 shadow-sm">
                  <Link to={`/applications/${app.id}`} className="block hover:text-indigo-600">
                    <p className="font-semibold leading-tight">{app.role || 'Untitled role'}</p>
                    <p className="text-sm text-slate-500">{app.company || 'Unknown company'}</p>
                  </Link>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <ScoreBadge score={app.match_score} />
                    <select
                      value={app.status}
                      onChange={(e) => move.mutate({ id: app.id, status: e.target.value as Status })}
                      className="rounded border border-slate-200 text-xs"
                      aria-label="Move to"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{LABELS[s]}</option>
                      ))}
                    </select>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )
      })}
    </div>
  )
}
