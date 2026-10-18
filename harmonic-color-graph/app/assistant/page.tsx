import { Assistant } from "@/components/assistant"
import { Suspense } from "react"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Assistant" }

export default function AssistantPage() {
  return <Suspense><Assistant /></Suspense>
}
