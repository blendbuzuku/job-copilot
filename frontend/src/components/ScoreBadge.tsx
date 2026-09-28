export function ScoreBadge({ score, large = false }: { score: number; large?: boolean }) {
  const color =
    score >= 75 ? 'bg-emerald-100 text-emerald-800' : score >= 50 ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
  const size = large ? 'text-2xl px-4 py-2' : 'text-xs px-2 py-0.5'
  return <span className={`${color} ${size} inline-block rounded-full font-semibold`}>{Math.round(score)}% match</span>
}
