import { Suspense } from "react"
import { RoutePreview } from "@/components/route-preview"

export default function GeneratePage() {
  return <Suspense><RoutePreview title="Generate" description="Shape a progression by key, tension, and color." status="The generator controls arrive in F64." /></Suspense>
}
