"use client"
import { useEffect, useRef } from "react"
import { noise3 } from "@/lib/motion/noise"
import { useReducedMotion } from "@/components/ambient/use-motion-preference"

type Props = { className?: string; particles?: number; interactive?: boolean; speed?: number }
const PALETTE = ["121,207,208", "169,149,236", "255,205,131", "140,174,215"]

/**
 * Particle swarm advected by a slowly evolving flow field. Particles leave soft trails, bend
 * around the pointer and are respawned at the edges. Pauses when hidden or off-screen and
 * renders a single still frame for visitors who prefer reduced motion.
 */
export function FlowField({ className = "", particles = 220, interactive = true, speed = 1 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const reduced = useReducedMotion()
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ctx = el.getContext("2d", { alpha: true })!
    let width = 0, height = 0, dpr = 1
    const pointer = { x: -9999, y: -9999, active: false }
    type P = { x: number; y: number; px: number; py: number; life: number; tone: number }
    let swarm: P[] = []
    const spawn = (p?: P): P => {
      const next = p ?? { x: 0, y: 0, px: 0, py: 0, life: 0, tone: 0 }
      next.x = next.px = Math.random() * width; next.y = next.py = Math.random() * height
      next.life = 120 + Math.random() * 280; next.tone = Math.random() < 0.55 ? 0 : Math.random() < 0.5 ? 1 : Math.random() < 0.6 ? 2 : 3
      return next
    }
    const resize = () => {
      const rect = el.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 1.5)
      width = rect.width; height = rect.height
      el.width = Math.round(width * dpr); el.height = Math.round(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const target = Math.round(particles * Math.min(1, (width * height) / (1440 * 900)) * (width < 640 ? 0.6 : 1))
      swarm = Array.from({ length: Math.max(40, target) }, () => spawn())
    }
    resize()
    let t = 0
    const step = (frames: number) => {
      for (let n = 0; n < frames; n++) {
        t += 0.0016 * speed
        ctx.globalCompositeOperation = "destination-out"
        ctx.fillStyle = "rgba(0,0,0,.075)"
        ctx.fillRect(0, 0, width, height)
        ctx.globalCompositeOperation = "lighter"
        ctx.lineWidth = 1.3
        for (const p of swarm) {
          const angle = noise3(p.x * 0.0021, p.y * 0.0021, t) * Math.PI * 3.2
          let vx = Math.cos(angle) * 1.15 * speed, vy = Math.sin(angle) * 1.15 * speed
          let glow = 0
          if (interactive && pointer.active) {
            const dx = pointer.x - p.x, dy = pointer.y - p.y, d2 = dx * dx + dy * dy
            if (d2 < 190 * 190) {
              const d = Math.sqrt(d2) + 1, pull = 1 - d / 190
              // Tangential swirl plus a gentle pull: the swarm orbits the cursor.
              vx += (-dy / d) * 2.6 * pull + (dx / d) * 0.9 * pull
              vy += (dx / d) * 2.6 * pull + (dy / d) * 0.9 * pull
              glow = pull
            }
          }
          p.px = p.x; p.py = p.y
          p.x += vx; p.y += vy; p.life -= 1
          if (p.life <= 0 || p.x < -10 || p.y < -10 || p.x > width + 10 || p.y > height + 10) { spawn(p); continue }
          ctx.strokeStyle = `rgba(${PALETTE[p.tone]},${0.5 + glow * 0.5})`
          ctx.beginPath(); ctx.moveTo(p.px, p.py); ctx.lineTo(p.x, p.y); ctx.stroke()
        }
      }
    }
    if (reduced) { step(160); return }
    const frameGap = particles > 150 ? 33 : 50
    let raf = 0, last = 0, running = true, visible = true
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop)
      if (!running || !visible || now - last < frameGap) return
      last = now; step(1)
    }
    const start = setTimeout(() => { raf = requestAnimationFrame(loop) }, 500)
    const onMove = (event: PointerEvent) => { const r = el.getBoundingClientRect(); pointer.x = event.clientX - r.left; pointer.y = event.clientY - r.top; pointer.active = true }
    const onLeave = () => { pointer.active = false }
    const onVisibility = () => { running = !document.hidden }
    const io = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting })
    io.observe(el)
    const ro = new ResizeObserver(resize); ro.observe(el)
    if (interactive) { window.addEventListener("pointermove", onMove, { passive: true }); document.addEventListener("pointerleave", onLeave) }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearTimeout(start); cancelAnimationFrame(raf); io.disconnect(); ro.disconnect()
      window.removeEventListener("pointermove", onMove); document.removeEventListener("pointerleave", onLeave); document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [particles, interactive, speed, reduced])
  return <canvas ref={ref} aria-hidden="true" className={`flow-field ${className}`} />
}
