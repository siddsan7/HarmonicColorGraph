import { Suspense } from "react"
import { RoutePreview } from "@/components/route-preview"

export default function SimilarPage() {
  return <Suspense><RoutePreview title="Similar" description="Find related progressions by structure and sound." status="Similarity exploration arrives in F65." /></Suspense>
}
