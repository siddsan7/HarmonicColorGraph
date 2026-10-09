import { Suspense } from "react"
import { GraphExplorer } from "@/components/graph-explorer"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Explore harmony" }

export default function ExplorePage() {
  return <Suspense><GraphExplorer /></Suspense>
}
