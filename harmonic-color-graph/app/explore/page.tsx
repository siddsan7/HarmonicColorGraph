import { Suspense } from "react"
import { RoutePreview } from "@/components/route-preview"

export default function ExplorePage() {
  return <Suspense><RoutePreview title="Explore" description="Inspect harmonic relationships and paths through the graph." status="The interactive graph arrives in F63." /></Suspense>
}
