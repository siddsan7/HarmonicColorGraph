"use client"

import { Play, Square } from "lucide-react"
import { Button } from "@/components/ui/button"

export function PlayButton({ playing, disabled, onPlay, onStop }: {
  playing: boolean
  disabled?: boolean
  onPlay: () => void
  onStop: () => void
}) {
  return <Button type="button" disabled={disabled} onClick={playing ? onStop : onPlay} aria-label={playing ? "Stop playback" : "Play progression"}>
    {playing ? <Square aria-hidden="true" /> : <Play aria-hidden="true" />}{playing ? "Stop" : "Play"}
  </Button>
}
