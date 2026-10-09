import { Suspense } from "react"
import { SimilarityExplorer } from "@/components/similarity-explorer"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Similar progressions" }

export default function SimilarPage() {
  return <Suspense><SimilarityExplorer /></Suspense>
}
