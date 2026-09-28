import { useQuery } from '@tanstack/react-query'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { api } from './api'
import ApplicationPage from './pages/ApplicationPage'
import BoardPage from './pages/BoardPage'
import NewApplicationPage from './pages/NewApplicationPage'
import ProfilePage from './pages/ProfilePage'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-200'}`

export default function App() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: api.health })

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3">
            <span className="mr-4 text-lg font-bold">💼 Job Copilot</span>
            <NavLink to="/" end className={linkClass}>Applications</NavLink>
            <NavLink to="/new" className={linkClass}>New application</NavLink>
            <NavLink to="/profile" className={linkClass}>My CV</NavLink>
          </nav>
        </header>
        {health?.demo_mode && (
          <div className="bg-amber-100 px-4 py-2 text-center text-sm text-amber-900">
            <strong>Demo mode:</strong> no API key found, so AI answers are simple examples. Add{' '}
            <code>ANTHROPIC_API_KEY</code> to <code>.env</code> and restart for real results.
          </div>
        )}
        <main className="mx-auto max-w-6xl px-4 py-6">
          <Routes>
            <Route path="/" element={<BoardPage />} />
            <Route path="/new" element={<NewApplicationPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/applications/:id" element={<ApplicationPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
