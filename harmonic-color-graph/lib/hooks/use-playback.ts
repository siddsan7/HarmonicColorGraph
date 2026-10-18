"use client"

import { useCallback, useEffect, useState } from "react"
import { PlaybackEngine, type Instrument, type PlaybackPosition, type PlaybackSequence } from "@/lib/music/engine"

export function usePlayback() {
  const [playing, setPlaying] = useState(false)
  const [position, setPosition] = useState<PlaybackPosition>(null)
  const [error, setError] = useState<string | null>(null)
  const [engine] = useState(() => new PlaybackEngine((active, current) => {
    setPlaying(active)
    setPosition(current)
  }))

  useEffect(() => {
    return () => engine.dispose()
  }, [engine])

  async function play(sequences: PlaybackSequence[], options: { bpm: number; loop: boolean; instrument: Instrument }) {
    setError(null)
    try {
      await engine.play(sequences, options)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Audio playback is unavailable.")
    }
  }

  const stop = useCallback(() => { engine.stop() }, [engine])

  return { playing, position, error, play, stop }
}
