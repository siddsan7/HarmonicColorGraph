import { Suspense } from "react"
import { Generator } from "@/components/generator"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Find an idea" }

export default function GeneratePage() {
  return <Suspense><Generator /></Suspense>
}
