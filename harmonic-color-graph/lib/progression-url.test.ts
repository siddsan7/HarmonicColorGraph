import { describe, expect, it } from "vitest"
import { readProgression, writeProgression } from "./progression-url"

describe("shareable progression", () => {
  it("restores the progression and context from a deep link", () => {
    expect(readProgression(new URLSearchParams("p=C-G-Am&k=C-major&g=pop&s=chorus"))).toEqual({
      input: "C - G - Am", key: "C major", genre: "pop", section: "chorus",
    })
  })

  it("updates only the shared fields and clears empty context", () => {
    const result = writeProgression(new URLSearchParams("view=list&g=jazz"), {
      input: "Cmaj7 - Em7 - Am7", key: "", genre: "pop", section: "",
    })
    expect(result.toString()).toBe("view=list&g=pop&p=Cmaj7-Em7-Am7&k=")
  })
})
