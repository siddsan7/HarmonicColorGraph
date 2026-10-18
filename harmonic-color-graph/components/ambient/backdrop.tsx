"use client"
import { usePathname } from "next/navigation"
import { FlowField } from "@/components/ambient/flow-field"
import { TopoLines } from "@/components/ambient/topo-lines"

/**
 * Fixed decorative layer behind every page: topographic contours with a drifting flow-field
 * swarm. The home page gets the full treatment; working pages stay quiet so music and
 * controls keep the focus, and the 3D atlas gets contours only to leave the GPU free.
 */
export function AmbientBackdrop() {
  const pathname = usePathname()
  const tone = pathname === "/" ? "hero" : pathname === "/explore" || pathname === "/teach" ? "calm" : "page"
  return <div className={`ambient ambient-${tone}`} aria-hidden="true">
    <div className="ambient-glow" />
    <TopoLines seed={tone === "hero" ? 3 : 7} />
    {tone !== "calm" && <FlowField particles={tone === "hero" ? 260 : 110} />}
    <div className="ambient-vignette" />
  </div>
}
