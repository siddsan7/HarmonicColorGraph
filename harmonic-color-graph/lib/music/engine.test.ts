import { beforeEach, describe, expect, it, vi } from "vitest"
import { PlaybackEngine, resolveVoicings, type PlaybackSequence } from "@/lib/music/engine"

const mocks = vi.hoisted(() => {
  const events: Array<{ at: number; callback: (time: number) => void }> = []
  const attacks = vi.fn()
  const transport = {
    bpm: { value: 120 }, loop: false, loopStart: 0, loopEnd: 0,
    schedule: vi.fn((callback: (time: number) => void, at: number) => { events.push({ callback, at }); return events.length }),
    scheduleOnce: vi.fn((callback: (time: number) => void, at: number) => { events.push({ callback, at }); return events.length }),
    start: vi.fn(), stop: vi.fn(), cancel: vi.fn(() => { events.length = 0 }),
  }
  return { events, attacks, transport, start: vi.fn(async () => {}), dispose: vi.fn(), releaseAll: vi.fn() }
})

vi.mock("tone", () => ({
  start: mocks.start,
  loaded: vi.fn(async () => {}),
  getTransport: () => mocks.transport,
  getDraw: () => ({ schedule: (callback: () => void) => callback() }),
  Frequency: (midi: number) => ({ toNote: () => `midi-${midi}` }),
  PolySynth: class {
    toDestination() { return this }
    triggerAttackRelease = mocks.attacks
    releaseAll = mocks.releaseAll
    dispose = mocks.dispose
  },
  Synth: class {},
  Sampler: class {
    toDestination() { return this }
    triggerAttackRelease = mocks.attacks
    releaseAll = mocks.releaseAll
    dispose = mocks.dispose
  },
}))

const progression: PlaybackSequence = {
  label: "A",
  chords: [
    { label: "C", pitchClasses: [0, 4, 7], voicing: [48, 60, 64, 67] },
    { label: "G", pitchClasses: [7, 11, 2], voicing: [43, 59, 62, 67] },
    { label: "Am", pitchClasses: [9, 0, 4], voicing: [45, 60, 64, 69] },
  ],
}

beforeEach(() => {
  mocks.events.length = 0
  vi.clearAllMocks()
})

describe("playback scheduling", () => {
  it.each([90, 120])("schedules four-beat chords and completion at %i BPM", async (bpm) => {
    const positions: Array<string> = []
    const engine = new PlaybackEngine((active, position) => {
      if (active && position) positions.push(`${position.sequence}:${position.chord}`)
    })
    await engine.play([progression], { bpm, loop: false, instrument: "synth" })
    const beat = 60 / bpm
    expect(mocks.start).toHaveBeenCalledOnce()
    expect(mocks.transport.bpm.value).toBe(bpm)
    expect(mocks.events.map((event) => event.at)).toEqual([0, 4 * beat, 8 * beat, 12 * beat])
    mocks.events.slice(0, 3).forEach((event) => event.callback(event.at))
    expect(mocks.attacks).toHaveBeenCalledWith(["midi-48", "midi-60", "midi-64", "midi-67"], beat * 3.7, 0)
    expect(positions).toEqual(["0:0", "0:1", "0:2"])
    mocks.events[3].callback(12 * beat)
    expect(mocks.transport.stop).toHaveBeenCalled()
    expect(mocks.dispose).toHaveBeenCalled()
  })

  it("plays A/B/C sequentially and loops across the entire comparison", async () => {
    const engine = new PlaybackEngine(() => {})
    await engine.play([progression, progression, progression], { bpm: 120, loop: true, instrument: "piano" })
    expect(mocks.events).toHaveLength(9)
    expect(mocks.events.map((event) => event.at)).toEqual([0, 2, 4, 6, 8, 10, 12, 14, 16])
    expect(mocks.transport.loop).toBe(true)
    expect(mocks.transport.loopEnd).toBe(18)
    engine.dispose()
    expect(mocks.transport.cancel).toHaveBeenCalledWith(0)
  })

  it("starts the audio context in the play gesture and ignores a stopped unlock", async () => {
    let unlock: (() => void) | undefined
    mocks.start.mockImplementationOnce(() => new Promise<void>((resolve) => { unlock = resolve }))
    const engine = new PlaybackEngine(() => {})
    const pending = engine.play([progression], { bpm: 120, loop: false, instrument: "synth" })
    expect(mocks.start).toHaveBeenCalledOnce()
    engine.stop()
    unlock?.()
    await pending
    expect(mocks.transport.start).not.toHaveBeenCalled()
  })

  it("uses supplied voicings and a playable local fallback", () => {
    const voiced = resolveVoicings([progression.chords[0], { label: "F", pitchClasses: [5, 9, 0] }])
    expect(voiced[0]).toEqual([48, 60, 64, 67])
    expect(voiced[1]).toHaveLength(4)
    expect(voiced[1].map((note) => note % 12)).toEqual([5, 5, 9, 0])
    expect(voiced[1].every((note) => note >= 36 && note <= 84)).toBe(true)
  })

  it("keeps the defining seventh in fallback voicings", () => {
    const [dominant, extended, inverted] = resolveVoicings([
      { label: "C7", pitchClasses: [0, 4, 7, 10] },
      { label: "C9", pitchClasses: [0, 4, 7, 10, 2] },
      { label: "C7/E", pitchClasses: [0, 4, 7, 10], bassPc: 4 },
    ])
    expect(new Set(dominant.map((note) => note % 12))).toEqual(new Set([0, 4, 7, 10]))
    expect(new Set(extended.map((note) => note % 12))).toEqual(new Set([0, 4, 7, 10, 2]))
    expect(inverted[0] % 12).toBe(4)
    expect(new Set(inverted.map((note) => note % 12))).toEqual(new Set([0, 4, 7, 10]))
  })
})
