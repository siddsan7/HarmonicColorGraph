type ToneModule = typeof import("tone")

let context: AudioContext | undefined
let tonePromise: Promise<ToneModule> | undefined

/** Resume within the click gesture, then load synthesis code on demand. */
export async function unlockAudio(): Promise<ToneModule> {
  const AudioContextClass = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AudioContextClass) throw new Error("Audio playback is unavailable in this browser.")
  context ??= new AudioContextClass()
  // This call must precede any await to preserve Safari/iOS gesture activation.
  const resumed = context.resume()
  tonePromise ??= import("tone").then((tone) => {
    tone.setContext(context!)
    return tone
  }).catch((error) => {
    tonePromise = undefined
    throw error
  })
  const [, tone] = await Promise.all([resumed, tonePromise])
  return tone
}
