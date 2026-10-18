import { TeachingPresentation } from "@/components/teaching-view"
import type { Metadata } from "next"

export const metadata: Metadata = { title: "Teaching view" }
export default function TeachingPage() { return <TeachingPresentation /> }
