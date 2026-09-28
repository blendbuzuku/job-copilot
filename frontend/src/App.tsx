import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import ApplicationPage from './pages/ApplicationPage'
import BoardPage from './pages/BoardPage'
import NewApplicationPage from './pages/NewApplicationPage'
import ProfilePage from './pages/ProfilePage'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium ${isActive ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-200'}`

export default function App() {
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
