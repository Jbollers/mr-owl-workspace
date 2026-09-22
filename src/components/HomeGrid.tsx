import type { WorkspaceEntity } from '../types'
import { entityHash } from '../lib/route'
import { categoryIcon } from '../lib/categories'
import MakCard from './MakCard'
import MakLogo from './MakLogo'

interface HomeGridProps {
  entities: WorkspaceEntity[]
  pinned: WorkspaceEntity[]
  grouped: Map<string, WorkspaceEntity[]>
  offline: boolean
  searching: boolean
  query: string
}

function greeting(): string {
  const h = new Date().getHours()
  if (h < 5) return 'A little night-owl planning?'
  if (h < 12) return 'Good morning, Mr. Bollers.'
  if (h < 18) return 'Good afternoon, Mr. Bollers.'
  return 'Good evening, Mr. Bollers.'
}

export default function HomeGrid({
  entities,
  pinned,
  grouped,
  offline,
  searching,
  query,
}: HomeGridProps) {
  const activeCount = entities.filter(e => e.status === 'active').length
  const categoryCount = new Set(entities.map(e => e.category || 'other')).size
  const shown = pinned.length + [...grouped.values()].reduce((n, list) => n + list.length, 0)

  return (
    <div className="home">
      <header className="home-hero">
        <MakLogo size={84} />
        <div>
          <p className="owl-eyebrow">MR. OWL · YOUR TEACHING NEST</p>
          <h1 className="home-title">{greeting()}</h1>
          <p className="home-sub">
            A little preparation. A world of discovery.</p>
          <p className="home-sub"><b>{activeCount}</b> active · <b>{entities.length}</b> projects ·{' '}
            <b>{categoryCount}</b> categories
            {offline && <span className="home-offline"> · workspace.json unreachable</span>}
          </p>
        </div>
      </header>

      {!searching && entities.some(e => e.id === 'teaching-studio' && e.status !== 'archived') && (
        <section className="teaching-launchpad" aria-label="Teaching workflows">
          <div className="teaching-intro"><span className="owl-eyebrow">LESS PREP. MORE POSSIBILITY.</span><h2>What are we teaching next?</h2><p>Your familiar teaching skills, ready when you are.</p></div>
          <div className="teaching-actions">
            <a href={entityHash('teaching-studio', 0)}><span className="teaching-number">01</span><strong>Plan a lesson</strong><span>Build from a topic, teacher guide or curriculum.</span><b aria-hidden="true">↗</b></a>
            <a href={entityHash('teaching-studio', 1)}><span className="teaching-number">02</span><strong>Format a plan</strong><span>Put approved content into your teacher-facing layout.</span><b aria-hidden="true">↗</b></a>
            <a href={entityHash('teaching-studio', 2)}><span className="teaching-number">03</span><strong>Adapt a deck</strong><span>Make room for the learning that matters.</span><b aria-hidden="true">↗</b></a>
            <a href={entityHash('teaching-studio', 3)}><span className="teaching-number">04</span><strong>Add teacher notes</strong><span>Keep your next question and scaffold close at hand.</span><b aria-hidden="true">↗</b></a>
            <a href={entityHash('teaching-studio', 4)}><span className="teaching-number">05</span><strong>Bring it indoors</strong><span>Turn an outdoor task into useful classroom evidence.</span><b aria-hidden="true">↗</b></a>
          </div>
          <p className="teaching-footnote">Open a workflow, then use its prompt with your source files in an agent chat.</p>
        </section>
      )}

      {searching && (
        <p className="home-filter">
          {shown === 0 ? 'No matches for' : `${shown} match${shown === 1 ? '' : 'es'} for`}{' '}
          “{query.trim()}” — archive included
        </p>
      )}

      {pinned.length > 0 && (
        <section className="home-section">
          <div className="section-head">
            <span className="section-title">{'\u{1F4CC}'} pinned</span>
            <span className="section-count">{pinned.length}</span>
          </div>
          <div className="card-grid">
            {pinned.map(e => (
              <MakCard key={e.id} entity={e} />
            ))}
          </div>
        </section>
      )}

      {[...grouped.entries()].map(([cat, list]) => (
        <section key={cat} className="home-section">
          <div className="section-head">
            <span className="section-title">
              {categoryIcon(cat)} {cat.replace(/-/g, ' ')}
            </span>
            <span className="section-count">{list.length}</span>
          </div>
          <div className="card-grid">
            {list.map(e => (
              <MakCard key={e.id} entity={e} />
            ))}
          </div>
        </section>
      ))}

      {shown === 0 && !searching && (
        <div className="home-empty">
          {offline
            ? 'Could not load workspace.json — is the public/workspace link in place? Run npm run dev again, Mr. Bollers.'
            : 'Nothing here yet. New work will appear as cards, Mr. Bollers.'}
        </div>
      )}
    </div>
  )
}
