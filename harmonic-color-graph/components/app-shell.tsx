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
    <header className={`shell-header${pathname === "/explore" ? " shell-atlas" : ""}`}>
      <a href="#main-content" className="skip-link">Skip to content</a>
      <div className="shell-header-inner">
        <Link href={hrefWithProgression("/", search)} className="shell-brand" aria-label="Harmonic Color Graph, Workbench">
          <span aria-hidden="true" className="shell-brand-mark">H<span>●</span>G</span>
          <span>Harmonic Color Graph</span>
        </Link>
        <nav aria-label="Primary navigation" className="shell-nav">
          {routes.map(({ href, label }) => <Link key={href} href={hrefWithProgression(href, search)} aria-current={pathname === href ? "page" : undefined}>{label}</Link>)}
        </nav>
      </div>
    </header>
    {children}
  </>
}
