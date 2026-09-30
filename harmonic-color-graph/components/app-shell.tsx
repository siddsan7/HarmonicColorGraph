"use client"

import Link from "next/link"
import { usePathname, useSearchParams } from "next/navigation"
import { hrefWithProgression } from "@/lib/progression-url"

const routes = [
  { href: "/", label: "Write music" },
  { href: "/explore", label: "Explore harmony" },
  { href: "/generate", label: "Find an idea" },
  { href: "/similar", label: "Similar" },
  { href: "/assistant", label: "Assistant" },
  { href: "/about", label: "About" },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const search = useSearchParams()

  return <>
    <header className="shell-header shell-atlas">
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="shell-header-inner">
        <Link href={hrefWithProgression("/", search)} className="shell-brand" aria-label="Harmonic Color Graph, Write music">
          <svg className="identity-mark" viewBox="0 0 48 32" aria-hidden="true"><path d="M5 7v18M5 16h12M17 7v18M42 10a10 10 0 1 0 0 12v-6h-8M19 16h10" fill="none" stroke="currentColor" strokeWidth="2.5"/><circle cx="20" cy="16" r="2.5" fill="var(--route-accent)"/><circle cx="28" cy="16" r="2.5" fill="var(--accent-secondary)"/></svg>
          <span>Harmonic Color Graph</span>
        </Link>
        <nav aria-label="Primary navigation" className="shell-nav">
          {routes.slice(0, 3).map(({ href, label }) => <Link key={href} href={hrefWithProgression(href, search)} aria-current={pathname === href ? "page" : undefined}>{label}</Link>)}
          <details className="nav-more"><summary aria-current={routes.slice(3).some((route) => route.href === pathname) ? "page" : undefined}>More{routes.slice(3).find((route) => route.href === pathname) ? ` · ${routes.find((route) => route.href === pathname)?.label}` : ""}<span aria-hidden="true">⌄</span></summary><div>{routes.slice(3).map(({ href, label }) => <Link key={href} href={hrefWithProgression(href, search)} aria-current={pathname === href ? "page" : undefined} onClick={(event) => event.currentTarget.closest("details")?.removeAttribute("open")}>{label}</Link>)}</div></details>
        </nav>
      </div>
    </header>
    {children}
    <footer className="site-footer"><span>H·G / Harmonic Color Graph</span><Link href={hrefWithProgression("/about", search)}>Musical model & data attribution</Link><span>Drafts stay on this device.</span></footer>
  </>
}
