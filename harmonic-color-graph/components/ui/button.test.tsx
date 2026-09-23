import { describe, expect, it } from "vitest"
import { render, screen } from "@testing-library/react"

import { Button } from "@/components/ui/button"

describe("Button", () => {
  it("renders its label and stays enabled by default", () => {
    render(<Button>Analyze</Button>)

    const button = screen.getByRole("button", { name: "Analyze" })
    expect(button).toBeInTheDocument()
    expect(button).toBeEnabled()
  })
})
