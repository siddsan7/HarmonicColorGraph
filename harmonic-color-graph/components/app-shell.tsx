"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect, useState } from "react"
import { MessageCircle, Orbit, PenLine, Sparkles, Waypoints } from "lucide-react"
import { motion } from "motion/react"
import { hrefWithProgression, writeProgression } from "@/lib/progression-url"
import { readStoredProgression } from "@/lib/sketches"

// Every destination is one tap away: no overflow menu to open first.
const routes = [
  { href: "/", label: "Write", icon: PenLine, hint: "Write music" },
  { href: "/explore", label: "Atlas", icon: Orbit, hint: "Explore harmony" },
  { href: "/generate", label: "Ideas", icon: Sparkles, hint: "Find an idea" },
  { href: "/similar", label: "Similar", icon: Waypoints, hint: "Find similar progressions" },
  { href: "/assistant", label: "Ask", icon: MessageCircle, hint: "Ask the assistant" },
]

// Tools that act on the current sketch. Opened without a shared link, they continue the saved draft.
const SKETCH_TOOLS = new Set(["/explore", "/generate", "/similar", "/assistant"])

function SketchGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const search = useSearchParams()
  const router = useRouter()
  const needsSketch = SKETCH_TOOLS.has(pathname) && !search.has("p")
  const [checked, setChecked] = useState<string | null>(null)
  useEffect(() => {
    if (!needsSketch) return
    const music = readStoredProgression()
    if (music?.input) router.replace(`${pathname}?${writeProgression(new URLSearchParams(window.location.search), music)}${window.location.hash}`, { scroll: false })
    else queueMicrotask(() => setChecked(pathname))
  }, [needsSketch, pathname, router])
  // Hold the tool for one frame rather than showing a stand-in sketch that the user did not write.
  if (needsSketch && checked !== pathname) return <main id="main-content" className="page" aria-busy="true" />
  return children
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const search = useSearchParams()
  return <>
    <header className="shell-header">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="shell-bar page">
        <Link href={hrefWithProgression("/", search)} className="shell-brand" aria-label="Harmonic Color Graph, Write music">
          <svg className="identity-mark" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="18" fill="var(--brand-purple)" /><circle cx="20" cy="20" r="7.5" fill="var(--brand-gold)" /><path d="M20 2a18 18 0 0 1 18 18" fill="none" stroke="var(--brand-gold)" strokeWidth="2.5" strokeLinecap="round" /></svg>
          <span>Harmonic <b>Color Graph</b></span>
        </Link>
        <nav aria-label="Primary navigation" className="shell-nav">
          {routes.map(({ href, label, icon: Icon, hint }) => {
            const active = pathname === href
            return <Link key={href} href={hrefWithProgression(href, search)} className="nav-link" aria-current={active ? "page" : undefined} title={hint}>
              {active && <motion.span layoutId="nav-lamp" className="nav-lamp" transition={{ type: "spring", stiffness: 300, damping: 30 }} />}
              <Icon className="nav-icon" size={17} aria-hidden="true" /><span className="nav-label">{label}</span>
            </Link>
          })}
        </nav>
        <Link href={hrefWithProgression("/about", search)} className="shell-about" aria-current={pathname === "/about" ? "page" : undefined}>About</Link>
      </div>
    </header>
    <SketchGate>{children}</SketchGate>
    <footer className="site-footer">
      <div className="site-footer-inner page">
        <span>Harmonic Color Graph</span>
        <span>Chord data: <a href="https://arxiv.org/abs/2410.22046">Chordonomicon (Kantarelis et al., 2024)</a>, <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC 4.0</a></span>
        <Link href={hrefWithProgression("/about", search)}>Musical model & limitations</Link>
        <span>Drafts stay on this device.</span>
      </div>
    </footer>
  </>
}
