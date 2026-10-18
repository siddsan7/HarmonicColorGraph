"use client"
import { useEffect, useRef } from "react"
import { fbm } from "@/lib/motion/noise"

/**
 * Topographic contour lines: marching squares over a smooth noise field, drawn once per
 * resize and drifted with CSS so the cost while idle is nil.
 */
export function TopoLines({ className = "", levels = 13, cell = 16, seed = 0 }: { className?: string; levels?: number; cell?: number; seed?: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const el = canvas.current
    if (!el) return
    const draw = () => {
      const bleed = 160
      const width = window.innerWidth + bleed, height = window.innerHeight + bleed
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
      el.width = Math.round(width * dpr); el.height = Math.round(height * dpr)
      el.style.width = `${width}px`; el.style.height = `${height}px`
      const ctx = el.getContext("2d")!
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, width, height)
      const cols = Math.ceil(width / cell) + 1, rows = Math.ceil(height / cell) + 1
      const scale = 0.0021
      const field = new Float32Array(cols * rows)
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) field[r * cols + c] = fbm(c * cell * scale + seed, r * cell * scale * 1.15 + seed * 0.7, 4.2)
      const lo = 0.22, hi = 0.8
      for (let l = 0; l < levels; l++) {
        const level = lo + ((hi - lo) * (l + 0.5)) / levels
        const major = l % 4 === 0
        ctx.beginPath()
        const lerpAt = (a: number, b: number) => (level - a) / (b - a || 1e-6)
        for (let r = 0; r < rows - 1; r++) for (let c = 0; c < cols - 1; c++) {
          const a = field[r * cols + c], b = field[r * cols + c + 1], d = field[(r + 1) * cols + c + 1], e = field[(r + 1) * cols + c]
          const idx = (a > level ? 8 : 0) | (b > level ? 4 : 0) | (d > level ? 2 : 0) | (e > level ? 1 : 0)
          if (idx === 0 || idx === 15) continue
          const x = c * cell, y = r * cell
          const top: [number, number] = [x + lerpAt(a, b) * cell, y]
          const right: [number, number] = [x + cell, y + lerpAt(b, d) * cell]
          const bottom: [number, number] = [x + lerpAt(e, d) * cell, y + cell]
          const left: [number, number] = [x, y + lerpAt(a, e) * cell]
          const seg = (p: [number, number], q: [number, number]) => { ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]) }
          switch (idx) {
            case 1: case 14: seg(left, bottom); break
            case 2: case 13: seg(bottom, right); break
            case 3: case 12: seg(left, right); break
            case 4: case 11: seg(top, right); break
            case 5: seg(top, left); seg(bottom, right); break
            case 10: seg(top, right); seg(left, bottom); break
            case 6: case 9: seg(top, bottom); break
            case 7: case 8: seg(top, left); break
          }
        }
        ctx.strokeStyle = major ? "rgba(168,196,235,.55)" : "rgba(140,174,215,.28)"
        ctx.lineWidth = major ? 1.1 : 0.8
        ctx.stroke()
      }
    }
    draw()
    let timer: ReturnType<typeof setTimeout> | undefined
    const onResize = () => { clearTimeout(timer); timer = setTimeout(draw, 200) }
    window.addEventListener("resize", onResize)
    return () => { clearTimeout(timer); window.removeEventListener("resize", onResize) }
  }, [levels, cell, seed])
  return <canvas ref={canvas} aria-hidden="true" className={`topo-lines ${className}`} />
}
