import { Suspense } from "react"
import { RoutePreview } from "@/components/route-preview"

export default function AboutPage() {
  return <Suspense><RoutePreview title="About" description="Harmonic Color Graph analyzes chord progressions through key, function, color, and evidence from musical relationships." status="Enter chords in the Workbench to see analysis, recommendations, and playback." /></Suspense>
}
