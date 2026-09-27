"use client"

import { PlayButton } from "@/components/play-button"
import type { Instrument, PlaybackPosition, PlaybackSequence } from "@/lib/music/engine"

export function Transport({ sequences, playing, position, error, bpm, loop, instrument, onBpmChange, onLoopChange, onInstrumentChange, onPlay, onStop }: {
  sequences: PlaybackSequence[]
  playing: boolean
  position: PlaybackPosition
  error: string | null
  bpm: number
  loop: boolean
  instrument: Instrument
  onBpmChange: (bpm: number) => void
  onLoopChange: (loop: boolean) => void
  onInstrumentChange: (instrument: Instrument) => void
  onPlay: () => void
  onStop: () => void
}) {
  const active = position && sequences[position.sequence]
  return <section className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-4" aria-label="Playback transport">
    <div className="flex flex-wrap items-end gap-4">
      <PlayButton playing={playing} disabled={!sequences.some((sequence) => sequence.chords.length)} onPlay={onPlay} onStop={onStop} />
      <label className="text-sm">Tempo
        <input className="ml-2 w-20 rounded border border-[var(--border-default)] bg-[var(--bg-subtle)] px-2 py-1" type="number" min={30} max={240} step={1} value={bpm} onChange={(event) => onBpmChange(Number(event.target.value))} /> BPM
      </label>
      <label className="text-sm">Instrument
        <select className="ml-2 rounded border border-[var(--border-default)] bg-[var(--bg-subtle)] px-2 py-1" value={instrument} onChange={(event) => onInstrumentChange(event.target.value as Instrument)}>
          <option value="synth">Synth</option><option value="piano">Sampled piano</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={loop} onChange={(event) => onLoopChange(event.target.checked)} />Loop</label>
    </div>
    <p className="mt-3 text-sm text-[var(--text-secondary)]" role="status" aria-live="polite">
      {playing ? active ? `Playing ${active.label}: ${active.chords[position.chord]?.label}` : "Starting playback…" : "Playback stopped"}
    </p>
    {error && <p className="mt-2 text-sm text-[var(--state-error)]" role="alert">{error}</p>}
  </section>
}
