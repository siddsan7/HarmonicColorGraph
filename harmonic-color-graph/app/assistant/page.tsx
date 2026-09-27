import { Suspense } from "react"
import { RoutePreview } from "@/components/route-preview"

export default function AssistantPage() {
  return <Suspense><RoutePreview title="Assistant" description="Ask grounded questions about a progression." status="The assistant arrives in F74." /></Suspense>
}
