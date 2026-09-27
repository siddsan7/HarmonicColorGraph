import { Midi } from "@tonejs/midi"
import { resolveVoicings, type PlaybackChord } from "@/lib/music/engine"

export function progressionMidi(chords: PlaybackChord[], bpm: number): Uint8Array {
  if (!Number.isFinite(bpm) || bpm < 30 || bpm > 240) throw new Error("Tempo must be between 30 and 240 BPM.")
  const midi = new Midi()
  midi.header.setTempo(bpm)
  const track = midi.addTrack()
  const beat = 60 / bpm
  resolveVoicings(chords).forEach((voicing, index) => {
    voicing.forEach((pitch) => track.addNote({ midi: pitch, time: index * 4 * beat, duration: 3.7 * beat, velocity: 0.8 }))
  })
  return midi.toArray()
}

export function midiFileName(chords: string[]): string {
  const slug = chords.join("-").toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "").slice(0, 80)
  return `hcg-${slug || "progression"}.mid`
}

export function downloadMidi(chords: PlaybackChord[], bpm: number): void {
  const bytes = progressionMidi(chords, bpm)
  const url = URL.createObjectURL(new Blob([Uint8Array.from(bytes)], { type: "audio/midi" }))
  const link = document.createElement("a")
  link.href = url
  link.download = midiFileName(chords.map((chord) => chord.label))
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
