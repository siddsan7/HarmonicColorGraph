import { Midi } from "@tonejs/midi"
import { describe, expect, it } from "vitest"
import { midiFileName, progressionMidi } from "@/lib/music/midi-export"

describe("MIDI export", () => {
  it("round trips voice-led notes and tempo", () => {
    const bytes = progressionMidi([
      { label: "Cmaj7", pitchClasses: [0, 4, 7, 11], voicing: [48, 60, 64, 67] },
      { label: "G7", pitchClasses: [7, 11, 2, 5], voicing: [43, 59, 62, 65] },
    ], 90)
    const parsed = new Midi(bytes)
    expect(parsed.header.tempos[0].bpm).toBeCloseTo(90, 2)
    expect(parsed.tracks[0].notes).toHaveLength(8)
    expect(parsed.tracks[0].notes.map((note) => note.midi)).toEqual([48, 60, 64, 67, 43, 59, 62, 65])
    expect(parsed.tracks[0].notes[4].time).toBeCloseTo(4 * 60 / 90, 2)
  })

  it("uses a safe progression filename", () => {
    expect(midiFileName(["Cmaj7", "F#7/C#", "G"])).toBe("hcg-cmaj7-f-7-c-g.mid")
  })
})
