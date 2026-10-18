"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { ChevronDown } from "lucide-react"
import { motion } from "motion/react"
import { hrefWithProgression, writeProgression } from "@/lib/progression-url"
import { readStoredProgression } from "@/lib/sketches"

const routes = [
  { href: "/", label: "Write music" },
  { href: "/explore", label: "Explore harmony" },
  { href: "/generate", label: "Find an idea" },
  { href: "/similar", label: "Similar" },
  { href: "/assistant", label: "Assistant" },
  { href: "/about", label: "About" },
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
  const more = useRef<HTMLDetailsElement>(null)
  const secondary = routes.slice(3)
  const currentSecondary = secondary.find((route) => route.href === pathname)

  useEffect(() => {
    // A disclosure menu should close like one: on outside press, Escape, or navigation.
    const menu = more.current
    if (!menu) return
    const close = (restoreFocus: boolean) => { if (!menu.open) return; menu.open = false; if (restoreFocus) menu.querySelector("summary")?.focus() }
    const onPointer = (event: PointerEvent) => { if (!menu.contains(event.target as Node)) close(false) }
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") close(menu.contains(document.activeElement)) }
    document.addEventListener("pointerdown", onPointer)
    document.addEventListener("keydown", onKey)
    return () => { document.removeEventListener("pointerdown", onPointer); document.removeEventListener("keydown", onKey) }
  }, [])
  useEffect(() => { if (more.current) more.current.open = false }, [pathname])

  return <>
    <header className="shell-header shell-atlas">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="shell-header-inner page">
        <Link href={hrefWithProgression("/", search)} className="shell-brand" aria-label="Harmonic Color Graph, Write music">
          <svg className="identity-mark" viewBox="0 0 48 32" aria-hidden="true"><path d="M5 7v18M5 16h12M17 7v18M42 10a10 10 0 1 0 0 12v-6h-8M19 16h10" fill="none" stroke="currentColor" strokeWidth="2.5"/><circle cx="20" cy="16" r="2.5" fill="var(--route-accent)"/><circle cx="28" cy="16" r="2.5" fill="var(--accent-secondary)"/></svg>
          <span>Harmonic Color Graph</span>
        </Link>
        <nav aria-label="Primary navigation" className="shell-nav">
          {routes.slice(0, 3).map(({ href, label }) => <Link key={href} href={hrefWithProgression(href, search)} className="nav-link" aria-current={pathname === href ? "page" : undefined}>{pathname === href && <motion.span layoutId="nav-pill" className="nav-pill" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}<span className="nav-label">{label}</span></Link>)}
          <details ref={more} className="nav-more">
            <summary aria-current={currentSecondary ? "page" : undefined}>{currentSecondary ? currentSecondary.label : "More"}<span className="sr-only">, more destinations</span><ChevronDown className="size-3.5" aria-hidden="true" /></summary>
            <div>{secondary.map(({ href, label }) => <Link key={href} href={hrefWithProgression(href, search)} aria-current={pathname === href ? "page" : undefined}>{label}</Link>)}</div>
          </details>
        </nav>
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
