import * as Tone from "tone"

export type PlaybackChord = {
  label: string
  pitchClasses: number[]
  bassPc?: number | null
  voicing?: number[]
}

export type PlaybackSequence = { label: string; chords: PlaybackChord[] }
export type Instrument = "synth" | "piano"
export type PlaybackPosition = { sequence: number; chord: number } | null

type ToneModule = typeof Tone
type Player = import("tone").PolySynth | import("tone").Sampler

/** Prefer the F40 voicing when present; otherwise keep each voice near its predecessor. */
export function resolveVoicings(chords: PlaybackChord[]): number[][] {
  let previous: number[] | null = null
  return chords.map((chord) => {
    const supplied = chord.voicing
    if (supplied?.length && supplied.every((note) => Number.isInteger(note) && note >= 0 && note <= 127)) {
      previous = [...supplied]
      return [...supplied]
    }
    const pcs = [...new Set(chord.pitchClasses.filter((pc) => Number.isInteger(pc) && pc >= 0 && pc < 12))]
    if (!pcs.length) return []
    const bassPc = chord.bassPc != null && pcs.includes(chord.bassPc) ? chord.bassPc : pcs[0]
    const basses = [36, 48, 60].flatMap((octave) => Array.from({ length: 12 }, (_, offset) => octave + offset)).filter((note) => note % 12 === bassPc && note <= 59)
    const bass = basses.sort((a, b) => Math.abs(a - (previous?.[0] ?? 48)) - Math.abs(b - (previous?.[0] ?? 48)) || a - b)[0]
    // Keep every distinct chord tone. A slash chord may put a tone other
    // than the root in the bass, so remove the actual bass from upper voices.
    const upperPcs = pcs.length >= 4 ? pcs.filter((pc) => pc !== bassPc) : [pcs[0], pcs[1] ?? pcs[0], pcs[2] ?? pcs[0]]
    const upper = upperPcs.map((pc, index) => {
      const target = previous?.[index + 1] ?? [60, 64, 67][index] ?? 60 + index * 3
      return Array.from({ length: 25 }, (_, step) => 60 + step).filter((note) => note % 12 === pc)
        .sort((a, b) => Math.abs(a - target) - Math.abs(b - target) || a - b)[0]
    })
    previous = [bass, ...upper]
    return previous
  })
}

export class PlaybackEngine {
  private tone: ToneModule | null = null
  private player: Player | null = null
  private generation = 0
  private position: PlaybackPosition = null
  private playing = false

  constructor(private onChange: (playing: boolean, position: PlaybackPosition) => void) {}

  async play(sequences: PlaybackSequence[], options: { bpm: number; loop: boolean; instrument: Instrument }): Promise<void> {
    this.stop()
    if (!sequences.some((item) => item.chords.length)) return
    if (!Number.isFinite(options.bpm) || options.bpm < 30 || options.bpm > 240) throw new Error("Tempo must be between 30 and 240 BPM.")
    const generation = this.generation
    // Call Tone.start synchronously within the click gesture for Safari/iOS unlock.
    const tone = Tone
    await tone.start()
    if (generation !== this.generation) return
    this.tone = tone
    const player: Player = options.instrument === "piano"
      ? new tone.Sampler({ urls: { C3: "C3.wav", C4: "C4.wav", C5: "C5.wav" }, baseUrl: "/samples/piano/" }).toDestination()
      : new tone.PolySynth(tone.Synth).toDestination()
    this.player = player
    try {
      if (options.instrument === "piano") await tone.loaded()
      if (generation !== this.generation) return
      const transport = tone.getTransport()
      transport.bpm.value = options.bpm
      const beatSeconds = 60 / options.bpm
      let offset = 0
      sequences.forEach((sequence, sequenceIndex) => {
        const voicings = resolveVoicings(sequence.chords)
        sequence.chords.forEach((_, chordIndex) => {
          const notes = voicings[chordIndex].map((midi) => tone.Frequency(midi, "midi").toNote())
          const position = { sequence: sequenceIndex, chord: chordIndex }
          transport.schedule((time) => {
            if (notes.length) player.triggerAttackRelease(notes, beatSeconds * 3.7, time)
            tone.getDraw().schedule(() => {
              if (generation === this.generation) this.emit(true, position)
            }, time)
          }, offset * beatSeconds)
          offset += 4
        })
      })
      const end = offset * beatSeconds
      transport.loop = options.loop
      transport.loopStart = 0
      transport.loopEnd = end
      if (!options.loop) transport.scheduleOnce((time) => {
        tone.getDraw().schedule(() => { if (generation === this.generation) this.stop() }, time)
      }, end)
      this.emit(true, null)
      transport.start("+0.05", 0)
    } catch (error) {
      if (generation === this.generation) this.stop()
      throw error
    }
  }

  stop(): void {
    this.generation++
    if (this.tone) {
      const transport = this.tone.getTransport()
      transport.stop()
      transport.cancel(0)
      transport.loop = false
    }
    this.player?.releaseAll()
    this.player?.dispose()
    this.player = null
    this.emit(false, null)
  }

  dispose(): void { this.stop() }

  private emit(playing: boolean, position: PlaybackPosition): void {
    this.playing = playing
    this.position = position
    this.onChange(this.playing, this.position)
  }
}
