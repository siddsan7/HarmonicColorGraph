// Small deterministic gradient-noise helpers for decorative motion only.
// Nothing here touches harmonic analysis; seeds are fixed so renders are stable.

const PERM = (() => {
  const p = new Uint8Array(512)
  const base = Array.from({ length: 256 }, (_, i) => i)
  let seed = 1337
  const rand = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 }
  for (let i = 255; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [base[i], base[j]] = [base[j], base[i]] }
  for (let i = 0; i < 512; i++) p[i] = base[i & 255]
  return p
})()

const fade = (t: number) => t * t * t * (t * (t * 6 - 15) + 10)
const lerp = (a: number, b: number, t: number) => a + (b - a) * t
function grad(hash: number, x: number, y: number, z: number) {
  const h = hash & 15
  const u = h < 8 ? x : y
  const v = h < 4 ? y : h === 12 || h === 14 ? x : z
  return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v)
}

/** Perlin noise in roughly [-1, 1]. */
export function noise3(x: number, y: number, z = 0) {
  const X = Math.floor(x) & 255, Y = Math.floor(y) & 255, Z = Math.floor(z) & 255
  x -= Math.floor(x); y -= Math.floor(y); z -= Math.floor(z)
  const u = fade(x), v = fade(y), w = fade(z)
  const A = PERM[X] + Y, AA = PERM[A] + Z, AB = PERM[A + 1] + Z
  const B = PERM[X + 1] + Y, BA = PERM[B] + Z, BB = PERM[B + 1] + Z
  return lerp(
    lerp(lerp(grad(PERM[AA], x, y, z), grad(PERM[BA], x - 1, y, z), u), lerp(grad(PERM[AB], x, y - 1, z), grad(PERM[BB], x - 1, y - 1, z), u), v),
    lerp(lerp(grad(PERM[AA + 1], x, y, z - 1), grad(PERM[BA + 1], x - 1, y, z - 1), u), lerp(grad(PERM[AB + 1], x, y - 1, z - 1), grad(PERM[BB + 1], x - 1, y - 1, z - 1), u), v),
    w,
  )
}

/** Two-octave fractal noise, normalised to roughly [0, 1]. */
export function fbm(x: number, y: number, z = 0) {
  return 0.5 + 0.5 * (noise3(x, y, z) * 0.7 + noise3(x * 2.1, y * 2.1, z) * 0.3)
}
