import { afterEach, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import AdminPage from "@/app/admin/page"

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it("sends the admin token only as a request header and handles rejection", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 403 })
  vi.stubGlobal("fetch", fetchMock)
  render(<AdminPage />)
  expect(fetchMock).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText("Admin token"), { target: { value: "private-test-token" } })
  fireEvent.click(screen.getByRole("button", { name: "Load metrics" }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
  expect(fetchMock.mock.calls[0][0]).toBe("/api/hcg/v2/admin/metrics")
  expect(fetchMock.mock.calls[0][1]).toEqual({
    headers: { "X-HCG-Jobs-Token": "private-test-token" }, cache: "no-store",
  })
  expect(await screen.findByRole("alert")).toHaveTextContent("The admin token was not accepted.")
  expect(window.location.search).toBe("")
})
