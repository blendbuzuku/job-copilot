import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Profile } from '../api'

export default function ProfilePage() {
  const { data: profile, error, isPending } = useQuery({ queryKey: ['profile'], queryFn: api.getProfile })

  if (isPending) return <p>Loading…</p>
  if (error) return <p className="text-rose-600">{error.message}</p>
  // The editor is only created once the CV has loaded, so it can start with the saved text
  return <CvEditor profile={profile} />
}

function CvEditor({ profile }: { profile: Profile }) {
  const queryClient = useQueryClient()
  const [cvText, setCvText] = useState(profile.cv_text)

  // A mutation is any request that changes data on the server
  const save = useMutation({
    mutationFn: (input: { file: File } | { text: string }) =>
      'file' in input ? api.uploadCv(input.file) : api.saveProfile(input.text),
    onSuccess: (updated) => {
      queryClient.setQueryData(['profile'], updated)
      setCvText(updated.cv_text) // after an upload, show the text we extracted
    },
  })

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold">My CV</h1>
        <p className="text-slate-600">
          Upload your full CV once. The AI only ever uses facts from this CV, so the more complete it is, the better.
        </p>
      </div>

      <label className="block rounded-lg border-2 border-dashed border-slate-300 bg-white p-6 text-center hover:border-indigo-400">
        <span className="font-medium text-indigo-600">Upload a PDF, .txt or .md file</span>
        <input
          type="file"
          accept=".pdf,.txt,.md"
          className="hidden"
          disabled={save.isPending}
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) save.mutate({ file })
          }}
        />
      </label>

      <p className="text-center text-sm text-slate-500">or paste it below</p>

      <textarea
        value={cvText}
        onChange={(e) => setCvText(e.target.value)}
        rows={18}
        placeholder="Paste your CV here…"
        className="w-full rounded-lg border border-slate-300 p-3 font-mono text-sm"
      />

      <div className="flex items-center gap-4">
        <button
          onClick={() => save.mutate({ text: cvText })}
          disabled={save.isPending || !cvText.trim()}
          className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {save.isPending ? 'Saving…' : 'Save CV'}
        </button>
        {save.isSuccess && (
          <p className="text-emerald-700">Saved. Your CV was split into {save.data.chunk_count} searchable pieces.</p>
        )}
        {save.isError && <p className="text-rose-600">{save.error.message}</p>}
      </div>
    </div>
  )
}
