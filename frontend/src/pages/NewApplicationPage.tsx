import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'

const STEPS = [
  'Reading the job posting…',
  'Finding evidence in your CV…',
  'Assessing your fit…',
  'Tailoring your CV and writing a cover letter…',
  'Fact-checking the new CV…',
]

export default function NewApplicationPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: api.getProfile })
  const [mode, setMode] = useState<'url' | 'text'>('url')
  const [jobUrl, setJobUrl] = useState('')
  const [jobText, setJobText] = useState('')
  const [step, setStep] = useState(0)

  const analyze = useMutation({
    mutationFn: () => api.analyze(mode === 'url' ? { job_url: jobUrl } : { job_text: jobText }),
    onMutate: () => setStep(0),
    onSuccess: (application) => {
      queryClient.invalidateQueries({ queryKey: ['applications'] }) // the board must reload
      navigate(`/applications/${application.id}`)
    },
  })
  const running = analyze.isPending

  // The backend does every step in one request; this only shows progress while we wait
  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 9000)
    return () => clearInterval(timer)
  }, [running])

  if (profile && !profile.cv_text.trim()) {
    return (
      <p>
        First, <Link to="/profile" className="text-indigo-600 underline">upload your CV</Link>.
      </p>
    )
  }

  const tab = (value: typeof mode, label: string) => (
    <button
      onClick={() => setMode(value)}
      className={`rounded-md px-3 py-1.5 text-sm font-medium ${mode === value ? 'bg-slate-800 text-white' : 'bg-slate-200'}`}
    >
      {label}
    </button>
  )

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold">New application</h1>
        <p className="text-slate-600">Give me a job posting and I'll tailor your CV and write a cover letter for it.</p>
      </div>

      <div className="flex gap-2">
        {tab('url', 'Job link')}
        {tab('text', 'Paste the text')}
      </div>

      {mode === 'url' ? (
        <input
          value={jobUrl}
          onChange={(e) => setJobUrl(e.target.value)}
          placeholder="https://…"
          className="w-full rounded-lg border border-slate-300 p-3"
        />
      ) : (
        <textarea
          value={jobText}
          onChange={(e) => setJobText(e.target.value)}
          rows={14}
          placeholder="Paste the full job posting…"
          className="w-full rounded-lg border border-slate-300 p-3 text-sm"
        />
      )}

      <button
        onClick={() => analyze.mutate()}
        disabled={running || !(mode === 'url' ? jobUrl.trim() : jobText.trim())}
        className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {running ? 'Working…' : 'Analyze and tailor'}
      </button>

      {running && (
        <div className="rounded-lg bg-indigo-50 p-4 text-indigo-900">
          <p className="font-medium">{STEPS[step]}</p>
          <p className="text-sm">This usually takes about a minute.</p>
        </div>
      )}
      {analyze.isError && <p className="text-rose-600">{analyze.error.message}</p>}
    </div>
  )
}
