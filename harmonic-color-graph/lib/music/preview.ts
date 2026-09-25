/** Play server supplied chord pitch classes in a short, quiet preview. */
export async function playChordSequence(chords: number[][]): Promise<void> {
  const context = new AudioContext()
  try {
    await context.resume()
    const start = context.currentTime + 0.03
    chords.forEach((pitchClasses, step) => {
      const at = start + step * 0.42
      for (const pitchClass of [...new Set(pitchClasses)].slice(0, 5)) {
        if (!Number.isInteger(pitchClass) || pitchClass < 0 || pitchClass > 11) continue
        const oscillator = context.createOscillator()
        const envelope = context.createGain()
        const midi = 60 + pitchClass
        oscillator.type = "sine"
        oscillator.frequency.value = 440 * 2 ** ((midi - 69) / 12)
        envelope.gain.setValueAtTime(0, at)
        envelope.gain.linearRampToValueAtTime(0.035, at + 0.015)
        envelope.gain.exponentialRampToValueAtTime(0.001, at + 0.34)
        oscillator.connect(envelope).connect(context.destination)
        oscillator.start(at)
        oscillator.stop(at + 0.36)
      }
    })
    const duration = chords.length * 420 + 150
    window.setTimeout(() => { void context.close() }, duration)
  } catch (error) {
    await context.close()
    throw error
  }
}
