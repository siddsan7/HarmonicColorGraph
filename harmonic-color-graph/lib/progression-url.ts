export type SharedProgression = {
  input: string
  key: string
  genre: string
  section: string
}

export const defaultProgression: SharedProgression = {
  input: "D7 - G - C",
  key: "C major",
  genre: "",
  section: "",
}

const fields = ["p", "k", "g", "s"] as const

export function readProgression(search: Pick<URLSearchParams, "get">): SharedProgression {
  const progression = search.get("p")
  return {
    input: progression === null ? defaultProgression.input : progression.split("-").map((chord) => chord.trim()).filter(Boolean).join(" - "),
    key: search.get("k")?.replaceAll("-", " ") ?? defaultProgression.key,
    genre: search.get("g") ?? "",
    section: search.get("s") ?? "",
  }
}

export function writeProgression(search: URLSearchParams, state: SharedProgression): URLSearchParams {
  const next = new URLSearchParams(search)
  const values = [
    state.input.split(/(?:\s*-\s*|\s*,\s*|\r?\n+|\s+)/).filter(Boolean).join("-"),
    state.key.trim().replace(/\s+/g, "-"),
    state.genre,
    state.section,
  ]
  fields.forEach((field, index) => {
    if (values[index] || index < 2) next.set(field, values[index])
    else next.delete(field)
  })
  return next
}

export function hrefWithProgression(path: string, search: Pick<URLSearchParams, "toString">): string {
  const query = search.toString()
  return query ? `${path}?${query}` : path
}
