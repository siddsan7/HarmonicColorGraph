import "@testing-library/jest-dom/vitest"

// jsdom lacks these browser APIs; motion components and the ambient layer feature-detect them.
class StubObserver { observe() {} unobserve() {} disconnect() {} takeRecords() { return [] } }
if (!("IntersectionObserver" in globalThis)) Object.assign(globalThis, { IntersectionObserver: StubObserver })
if (!("ResizeObserver" in globalThis)) Object.assign(globalThis, { ResizeObserver: StubObserver })
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = ((query: string) => ({ matches: false, media: query, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false })) as typeof window.matchMedia
}
