"use client"

import { useEffect, useRef, useState, type KeyboardEvent, type RefObject } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Maximize2, Minimize2, Minus, Plus, ScanSearch } from "lucide-react"
import type { ForceGraph3DInstance } from "3d-force-graph"
import type { Color, Group, Sprite, Mesh, MeshBasicMaterial, SpriteMaterial, PerspectiveCamera } from "three"
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { Dock, DockIcon } from "@/components/ui/dock"
import { ATLAS_COLORS, atlasData, nodeColor, nodeLabel, type AtlasNode, type AtlasLink } from "@/lib/graph/atlas"
import type { GraphData } from "@/lib/graph/data"
import { functionExplanation, type AtlasView } from "@/lib/graph/presentation"

type Props = {
  graph: GraphData; selected: string; pathNodes: string[]; pathEdges: string[]; colorAxis: string
  onSelect: (id: string) => void; onListView?: () => void; initialView?: AtlasView | null
  captureRef?: RefObject<(() => AtlasView) | null>; fullscreenTarget?: RefObject<HTMLElement | null>
  /** Chords worth trying next: they pulse softly and keep their labels. */
  candidateNodes?: string[]
  /** Change this value to bring the whole active route into view. */
  fitRouteKey?: number
}
type Tip = { id: string; label: string; kind: string; text: string; links: number; moves: { label: string; prob: number | null }[] }
type Atlas = ForceGraph3DInstance<AtlasNode, AtlasLink>
type NodeVisual = { group: Group; core: Mesh; halo: Sprite; ring: Sprite; label: Sprite; updateLabel: (text: string) => void; dispose: () => void }
type FitMode = "all" | "path" | "selected" | "reset"
type Runtime = { graph: Atlas; visuals: Map<string, NodeVisual>; refresh: () => void; arrive: (ids: string[], first: boolean) => void; fit: (mode: FitMode) => void; zoom: (factor: number) => void; orbit: (yaw: number, pitch: number) => void; wake: (ms?: number) => void; dispose: () => void }

const ROUTE = ATLAS_COLORS.route
const INK = "#f4f1ea"
/** Above this many chords the map stays still: per-frame link updates would cost more than the motion is worth. */
const FLOAT_LIMIT = 220
const ARRIVE_MS = 900
const CAMERA_MS = 900
const NO_IDS: string[] = []

/** Stable 0..1 value per id, so every chord keeps its own rhythm between renders. */
function seed(id: string, salt: number) {
  let hash = 2166136261 ^ salt
  for (let index = 0; index < id.length; index++) hash = Math.imul(hash ^ id.charCodeAt(index), 16777619)
  return (hash >>> 0) / 4294967295
}

export function GraphCanvas(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const runtime = useRef<Runtime | null>(null)
  const latest = useRef(props)
  const [ready, setReady] = useState(false)
  const [failure, setFailure] = useState("")
  const [hover, setHover] = useState("")
  const [tip, setTip] = useState<Tip | null>(null)
  const tipRef = useRef<HTMLDivElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const [fullScreen, setFullScreen] = useState(false)
  const [reduced, setReduced] = useState(false)
  useEffect(() => { latest.current = props })
  // Full screen keeps the surrounding workspace (route, chord card) when the host provides it.
  const fullscreenElement = () => props.fullscreenTarget?.current ?? stage.current
  useEffect(() => { const update = () => setFullScreen(!!document.fullscreenElement && document.fullscreenElement === (latest.current.fullscreenTarget?.current ?? stage.current)); document.addEventListener("fullscreenchange", update); return () => document.removeEventListener("fullscreenchange", update) }, [])

  useEffect(() => {
    let disposed = false
    let cleanup = () => {}
    async function mount() {
      try {
        const [THREE, { default: ForceGraph }] = await Promise.all([import("three"), import("3d-force-graph")])
        if (disposed || !container.current) return
        const host = container.current
        const media = window.matchMedia("(prefers-reduced-motion: reduce)")
        setReduced(media.matches)
        const graph = new ForceGraph(host, { controlType: "orbit", rendererConfig: { antialias: true, alpha: true, powerPreference: "high-performance" } }) as unknown as Atlas
        let cleaned = false
        const owned = new Set<{ dispose: () => void }>()
        const releaseGPU = () => { if (cleaned) return; cleaned = true; graph.pauseAnimation(); graph._destructor(); owned.forEach((resource) => resource.dispose()); graph.renderer().dispose(); graph.renderer().forceContextLoss(); host.replaceChildren() }
        cleanup = releaseGPU
        const controls = graph.controls() as OrbitControls
        const camera = graph.camera() as PerspectiveCamera
        camera.near = 1
        camera.updateProjectionMatrix()
        controls.enableDamping = !media.matches
        controls.dampingFactor = .08
        controls.minDistance = 40
        controls.maxDistance = 1400
        controls.rotateSpeed = .55
        controls.zoomSpeed = .7
        controls.screenSpacePanning = true
        graph.renderer().setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
        graph.renderer().setClearColor(0x17161a, 0)
        // Positions come from the deterministic layout. The engine keeps ticking only so that
        // connections follow their chords while the map floats; its forces are switched off.
        graph.backgroundColor("#00000000").showNavInfo(false).numDimensions(3).enableNodeDrag(false)
          .warmupTicks(0).cooldownTicks(Infinity).cooldownTime(Infinity).d3AlphaMin(0).nodeLabel("").linkLabel("").linkOpacity(.8)
          .linkCurvature("curvature").linkCurveRotation("rotation").linkResolution(12)
          .linkDirectionalArrowRelPos(.79).linkDirectionalArrowResolution(12)
          .linkDirectionalParticles(0).linkDirectionalParticleWidth(1.7).linkDirectionalParticleColor(() => ROUTE).linkDirectionalParticleSpeed(.011)
        graph.d3Force("charge", null); graph.d3Force("center", null)
        ;(graph.d3Force("link") as unknown as { strength?: (value: number) => void } | undefined)?.strength?.(0)
        const visuals = new Map<string, NodeVisual>()
        // Per-chord eased state: hover growth, route ignition flash, dimming, label and arrival fades, drift rhythm.
        type Dyn = { h: number; t: number; flash: number; dim: number; dimT: number; base: number; hb: number; pin: boolean; label: number; labelT: number; enter: number; phase: number; speed: number; tint: Color }
        const anim = new Map<string, Dyn>()
        const dyn = (id: string) => { let d = anim.get(id); if (!d) { d = { h: 0, t: 0, flash: 0, dim: 0, dimT: 0, base: 1, hb: .45, pin: false, label: 0, labelT: 0, enter: 1, phase: seed(id, 1) * Math.PI * 2, speed: 1.05 + seed(id, 2) * .5, tint: new THREE.Color(INK) }; anim.set(id, d) } return d }
        // Chords that are still travelling to their place: where they started and when.
        const arrivals = new Map<string, { x: number; y: number; z: number; at: number }>()
        let candidates = new Set<string>(), lastRoute = new Set<string>(), raf = 0, hoveredNode = "", styled = 0
        const routeParticles = (link: AtlasLink) => { const p = latest.current; return p.pathEdges.includes(link.id) && !media.matches ? (link.id === p.pathEdges.at(-1) ? 5 : 2) : 0 }
        const sphere = new THREE.SphereGeometry(3.2, 16, 12); owned.add(sphere)
        // Taps hit a modest invisible target, never a neighbour's glow, ring or label.
        const hitSphere = new THREE.SphereGeometry(6, 8, 6); owned.add(hitSphere)
        const hitMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }); owned.add(hitMaterial)
        const ignoreRay = () => {}
        function texture(draw: (ctx: CanvasRenderingContext2D, size: number) => void, size = 128) {
          const canvas = document.createElement("canvas"); canvas.width = size; canvas.height = size
          const ctx = canvas.getContext("2d")!
          draw(ctx, size)
          const image = new THREE.CanvasTexture(canvas); image.colorSpace = THREE.SRGBColorSpace
          owned.add(image); return image
        }
        const glow = texture((ctx, size) => {
          const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
          gradient.addColorStop(0, "rgba(255,255,255,.7)"); gradient.addColorStop(.25, "rgba(255,255,255,.18)"); gradient.addColorStop(1, "rgba(255,255,255,0)")
          ctx.fillStyle = gradient; ctx.fillRect(0, 0, size, size)
        })
        const ring = texture((ctx, size) => { ctx.strokeStyle = "#fff"; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(size / 2, size / 2, size * .38, 0, Math.PI * 2); ctx.stroke() })
        const labelShown = (id: string) => {
          const p = latest.current
          return (!p.pathNodes.length && graph.graphData().nodes.length <= 20) || id === p.selected || p.pathNodes.includes(id) || id === hoveredNode || candidates.has(id)
        }
        function buildNode(node: AtlasNode) {
          const existing = visuals.get(node.id)
          if (existing) return existing.group
          const group = new THREE.Group()
          const d = dyn(node.id)
          const isRoute = latest.current.pathNodes.includes(node.id)
          d.tint.set(isRoute ? ROUTE : nodeColor(node, latest.current.colorAxis))
          const coreMaterial = new THREE.MeshBasicMaterial({ color: d.tint, transparent: true, depthTest: false, depthWrite: false })
          const core = new THREE.Mesh(sphere, coreMaterial)
          // Keep small, screen-sized points legible above crossing connections and grid lines.
          core.renderOrder = 20
          const haloMaterial = new THREE.SpriteMaterial({ map: glow, color: d.tint, transparent: true, depthWrite: false, sizeAttenuation: false, blending: THREE.AdditiveBlending })
          const halo = new THREE.Sprite(haloMaterial); halo.scale.set(32, 32, 1)
          const ringMaterial = new THREE.SpriteMaterial({ map: ring, color: ROUTE, transparent: true, depthWrite: false, sizeAttenuation: false })
          const selection = new THREE.Sprite(ringMaterial); selection.scale.set(16, 16, 1); selection.visible = false
          const drawLabel = (ctx: CanvasRenderingContext2D, size: number, text: string) => {
            ctx.clearRect(0, 0, size, size)
            ctx.font = "600 44px Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
            ctx.shadowColor = "#17161a"; ctx.shadowBlur = 12; ctx.fillStyle = INK
            ctx.fillText(text, size / 2, size / 2, size - 8)
          }
          let currentLabel = nodeLabel(node)
          const labelTexture = texture((ctx, size) => drawLabel(ctx, size, currentLabel), 256)
          const labelMaterial = new THREE.SpriteMaterial({ map: labelTexture, transparent: true, depthWrite: false, sizeAttenuation: false, opacity: 0 })
          const label = new THREE.Sprite(labelMaterial); label.scale.set(.13, .13, 1); label.position.set(0, 11, 0)
          d.labelT = labelShown(node.id) ? 1 : 0
          if (media.matches) d.label = d.labelT
          label.visible = d.label > .02
          halo.raycast = ignoreRay; selection.raycast = ignoreRay; label.raycast = ignoreRay
          group.add(new THREE.Mesh(hitSphere, hitMaterial), halo, core, selection, label)
          const nodeResources = [coreMaterial, haloMaterial, ringMaterial, labelMaterial, labelTexture]
          nodeResources.forEach((resource) => owned.add(resource))
          visuals.set(node.id, { group, core, halo, ring: selection, label, updateLabel: (text) => { if (text === currentLabel) return; currentLabel = text; const canvas = labelTexture.image as HTMLCanvasElement; drawLabel(canvas.getContext("2d")!, 256, text); labelTexture.needsUpdate = true }, dispose: () => { nodeResources.forEach((resource) => { resource.dispose(); owned.delete(resource) }); group.removeFromParent() } })
          return group
        }
        graph.nodeThreeObject(buildNode)
        // A faint floor and slow dust convey depth without inventing data or a measured similarity axis.
        const grid = new THREE.GridHelper(420, 20, 0x4a4358, 0x2c2933)
        grid.position.y = -120
        const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]
        gridMaterials.forEach((material) => { material.transparent = true; material.opacity = .16; owned.add(material) })
        owned.add(grid.geometry); graph.scene().add(grid)
        const dustGeometry = new THREE.BufferGeometry()
        const dustPositions = new Float32Array(240 * 3)
        for (let index = 0; index < 240; index++) {
          const radius = 180 + seed(`dust${index}`, 3) * 420, theta = seed(`dust${index}`, 4) * Math.PI * 2, tilt = Math.acos(2 * seed(`dust${index}`, 5) - 1)
          dustPositions.set([radius * Math.sin(tilt) * Math.cos(theta), radius * Math.cos(tilt) * .6, radius * Math.sin(tilt) * Math.sin(theta)], index * 3)
        }
        dustGeometry.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3))
        const dustMaterial = new THREE.PointsMaterial({ color: 0xb9a6d6, size: 1.6, sizeAttenuation: false, transparent: true, opacity: .34, depthWrite: false })
        const dust = new THREE.Points(dustGeometry, dustMaterial)
        dust.raycast = ignoreRay
        owned.add(dustGeometry); owned.add(dustMaterial); graph.scene().add(dust)

        let timer: ReturnType<typeof setTimeout> | undefined
        let visible = true
        let active = false
        // The map keeps drifting while it is on screen; "active" only marks a user or camera interaction in progress.
        const drifting = () => !media.matches && visible && !document.hidden
        const settle = () => { if (active || disposed) return; if (drifting()) host.dataset.rendering = "ambient"; else { graph.pauseAnimation(); host.dataset.rendering = "paused" } }
        const wake = (ms = 1000) => {
          if (disposed || !visible || document.hidden) return
          graph.resumeAnimation(); host.dataset.rendering = "active"
          clearTimeout(timer)
          timer = setTimeout(settle, ms)
        }
        const scratch = new THREE.Vector3(), lift = new THREE.Vector3()
        let cameraKey = ""
        function frame(now: number) {
          camera.updateMatrixWorld()
          const tangent = 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, host.clientHeight)
          const labelScale = 82 * tangent
          const p = latest.current, breathing = drifting(), time = now / 1000
          graph.graphData().nodes.forEach((node) => {
            const visual = visuals.get(node.id)
            if (!visual) return
            const important = p.selected === node.id || p.pathNodes.includes(node.id)
            const depth = Math.max(1, scratch.set(node.x, node.y, node.z).applyMatrix4(camera.matrixWorldInverse).z * -1)
            const d = anim.get(node.id), h = d?.h ?? 0, flash = d?.flash ?? 0, cand = candidates.has(node.id)
            const pulse = cand && breathing ? .5 + .5 * Math.sin(time * 2.4 + (d?.phase ?? 0)) : .5
            const breath = breathing && d ? 1 + .07 * Math.sin(time * d.speed + d.phase) : 1
            visual.core.scale.setScalar(depth * tangent * (important ? 5 : 3.5) / 3.2 * (1 + .8 * h + .55 * flash))
            visual.label.scale.set(labelScale, labelScale, 1)
            visual.label.position.copy(lift.set(0, depth * tangent * 17 * (1 + .5 * h), 0).applyQuaternion(camera.quaternion))
            visual.halo.scale.setScalar(tangent * (important ? 44 : 32) * (1 + 1.1 * h + 1.4 * flash) * breath)
            visual.ring.scale.setScalar(tangent * 24 * (1 + .45 * h + flash * .9 + (cand ? .25 * pulse : 0)))
            visual.ring.visible = !!d?.pin || cand || h > .04 || flash > .04
            const ringMaterial = visual.ring.material as SpriteMaterial
            ringMaterial.color.set(cand ? ROUTE : h > .04 && !d?.pin ? INK : p.selected === node.id ? INK : ROUTE)
            ringMaterial.opacity = (cand ? .35 + .5 * pulse : Math.max(0, Math.min(1, d?.pin ? 1 : h + flash))) * (d?.enter ?? 1)
          })
          placeTip()
          const position = graph.cameraPosition()
          const key = `${position.x}|${position.y}|${position.z}|${controls.target.x}|${controls.target.y}|${controls.target.z}`
          if (key !== cameraKey) { cameraKey = key; host.dataset.camera = JSON.stringify(position); host.dataset.target = JSON.stringify(controls.target) }
        }
        // Read-only inspection on demand; no scene-sized serialization in the render loop.
        const diagnosticHost = host as HTMLDivElement & { atlasSnapshot?: () => unknown }
        diagnosticHost.atlasSnapshot = () => {
          const width = graph.linkWidth(), color = graph.linkColor()
          return {
            clipping: { near: (graph.camera() as PerspectiveCamera).near, far: (graph.camera() as PerspectiveCamera).far },
            screenNodes: graph.graphData().nodes.map((node) => ({ id: node.id, ...graph.graph2ScreenCoords(node.x, node.y, node.z) })),
            nodes: graph.graphData().nodes.map((node) => ({ id: node.id, color: (visuals.get(node.id)?.core.material as MeshBasicMaterial | undefined)?.color.getHexString() })),
            edges: graph.graphData().links.map((link) => ({ id: link.id, width: typeof width === "function" ? width(link) : width, color: typeof color === "function" ? color(link) : color })),
          }
        }
        const onChange = () => { frame(performance.now()); wake() }
        const onStart = () => { active = true; wake() }
        const onEnd = () => { active = false; wake() }
        controls.addEventListener("change", onChange); controls.addEventListener("start", onStart); controls.addEventListener("end", onEnd)
        const onPointer = () => wake()
        host.addEventListener("pointermove", onPointer); host.addEventListener("pointerdown", onPointer); host.addEventListener("wheel", onPointer, { passive: true })
        function placeTip() {
          const el = tipRef.current
          const node = hoveredNode ? graph.graphData().nodes.find((item) => item.id === hoveredNode) : undefined
          if (!el || !node) return
          const point = graph.graph2ScreenCoords(node.x, node.y, node.z)
          el.style.transform = `translate(${Math.max(140, Math.min(host.clientWidth - 140, point.x))}px, ${point.y}px)`
          el.dataset.side = point.y < 190 ? "below" : "above"
        }
        /** Moves every chord: easing new arrivals into place and letting settled ones bob around their resting point. */
        function drift(now: number) {
          const nodes = graph.graphData().nodes, still = media.matches || nodes.length > FLOAT_LIMIT, time = now / 1000
          const swell = 4 * Math.sin(time * .62)
          let travelling = false
          for (const node of nodes) {
            const d = dyn(node.id), arrival = arrivals.get(node.id)
            let progress = 1
            if (arrival) {
              const elapsed = (now - arrival.at) / ARRIVE_MS
              if (media.matches || elapsed >= 1) arrivals.delete(node.id)
              else { progress = elapsed <= 0 ? 0 : 1 - (1 - elapsed) ** 3; travelling = true }
            }
            d.enter = progress
            const from = arrival && progress < 1 ? arrival : null
            // Each chord bobs to its own rhythm, on top of one slow swell that lifts the whole map together.
            const sway = still ? 0 : progress
            node.fx = (from ? from.x + (node.rx - from.x) * progress : node.rx) + sway * 1.6 * Math.sin(time * d.speed * .7 + d.phase * 1.7)
            node.fy = (from ? from.y + (node.ry - from.y) * progress : node.ry) + sway * (5.5 * Math.sin(time * d.speed + d.phase) + swell)
            node.fz = (from ? from.z + (node.rz - from.z) * progress : node.rz) + sway * 1.6 * Math.cos(time * d.speed * .6 + d.phase)
          }
          if (!media.matches) dust.rotation.y = time * .012
          return travelling
        }
        function loop(now: number) {
          raf = 0
          let moving = false
          // Chords are drawn a frame or two after their data arrives; style any that appeared since the last pass.
          if (visuals.size !== styled) { styled = visuals.size; refresh() }
          if (hoveredNode && !visuals.has(hoveredNode)) { hoveredNode = ""; setTip(null) }
          const travelling = drift(now)
          anim.forEach((d, id) => {
            const visual = visuals.get(id)
            if (!visual) { anim.delete(id); return }
            if (Math.abs(d.t - d.h) > .002) { d.h += (d.t - d.h) * .12; moving = true } else d.h = d.t
            if (d.flash > .003) { d.flash *= .94; moving = true } else d.flash = 0
            if (Math.abs(d.dimT - d.dim) > .004) { d.dim += (d.dimT - d.dim) * .09; moving = true } else d.dim = d.dimT
            if (Math.abs(d.labelT - d.label) > .01) { d.label += (d.labelT - d.label) * .14; moving = true } else d.label = d.labelT
            const core = visual.core.material as MeshBasicMaterial, halo = visual.halo.material as SpriteMaterial
            // Colour changes cross-fade; the last small step snaps so the tint lands exactly on its target.
            if (!core.color.equals(d.tint)) {
              if (media.matches || Math.abs(core.color.r - d.tint.r) + Math.abs(core.color.g - d.tint.g) + Math.abs(core.color.b - d.tint.b) < .012) core.color.copy(d.tint)
              else { core.color.lerp(d.tint, .14); moving = true }
              halo.color.copy(core.color)
            }
            const shade = (1 - .6 * d.dim) * d.enter
            core.opacity = d.base * shade
            halo.opacity = Math.min(1, d.hb * (1 + .9 * d.h + .8 * d.flash)) * shade
            visual.label.visible = d.label > .02
            ;(visual.label.material as SpriteMaterial).opacity = d.label * Math.max(.3, d.base) * d.enter
          })
          frame(now)
          if (!visible || document.hidden) return
          // refresh() above may already have queued the next frame; never run two loops at once.
          if (raf) return
          if (drifting()) raf = requestAnimationFrame(loop)
          else if (moving || travelling) { wake(500); raf = requestAnimationFrame(loop) }
        }
        const kick = () => { if (!raf && !disposed && !document.hidden) raf = requestAnimationFrame(loop) }
        function fit(mode: FitMode) {
          const p = latest.current
          const nodes = graph.graphData().nodes.filter((node) => mode === "selected" ? node.id === p.selected : mode === "path" ? p.pathNodes.includes(node.id) : true)
          if (!nodes.length) return
          // Frame the resting layout, not wherever the chords have drifted to this instant.
          const center = new THREE.Vector3()
          nodes.forEach((node) => center.add(new THREE.Vector3(node.rx, node.ry, node.rz))); center.divideScalar(nodes.length)
          const tangent = Math.tan(camera.fov * Math.PI / 360)
          const direction = mode === "reset" ? new THREE.Vector3(.8, .5, 1).normalize() : new THREE.Vector3().copy(camera.position).sub(controls.target).normalize()
          const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), direction).normalize()
          const up = new THREE.Vector3().crossVectors(direction, right).normalize()
          let distance = mode === "selected" ? 75 : 90
          nodes.forEach((node) => {
            const delta = new THREE.Vector3(node.rx, node.ry, node.rz).sub(center)
            const depth = delta.dot(direction)
            distance = Math.max(distance, depth + Math.abs(delta.dot(right)) / (tangent * camera.aspect) * 1.3, depth + Math.abs(delta.dot(up)) / tangent * Math.max(1.5, host.clientHeight / Math.max(150, host.clientHeight - 160)))
          })
          center.addScaledVector(up, -distance * tangent * (host.clientWidth < 600 ? 110 : 65) / host.clientHeight)
          controls.maxDistance = Math.max(1400, distance * 3)
          camera.far = controls.maxDistance * 4
          camera.updateProjectionMatrix()
          const target = center.clone().addScaledVector(direction, distance)
          wake(CAMERA_MS + 400); graph.cameraPosition(target, center, media.matches ? 0 : CAMERA_MS)
          if (media.matches) { controls.update(); graph.camera().updateMatrixWorld(); frame(performance.now()) }
        }
        function zoom(factor: number) {
          const offset = camera.position.clone().sub(controls.target)
          const distance = Math.max(controls.minDistance, Math.min(controls.maxDistance, offset.length() * factor))
          const position = offset.setLength(distance).add(controls.target)
          wake(); graph.cameraPosition(position, controls.target, media.matches ? 0 : 420)
        }
        function orbit(yaw: number, pitch: number) {
          const offset = camera.position.clone().sub(controls.target)
          const spherical = new THREE.Spherical().setFromVector3(offset)
          spherical.theta += yaw
          spherical.phi = Math.max(.15, Math.min(Math.PI - .15, spherical.phi + pitch))
          const position = new THREE.Vector3().setFromSpherical(spherical).add(controls.target)
          wake(); graph.cameraPosition(position, controls.target, media.matches ? 0 : 420)
        }
        function refresh() {
          const p = latest.current, route = new Set(p.pathNodes), pathEdges = new Set(p.pathEdges)
          // Newly lit chords flash so building a route feels like switching pathways on.
          p.pathNodes.forEach((id) => { if (!lastRoute.has(id)) dyn(id).flash = 1 })
          lastRoute = route
          candidates = new Set(p.candidateNodes ?? NO_IDS)
          const count = graph.graphData().nodes.length
          graph.graphData().nodes.forEach((node) => {
            const visual = visuals.get(node.id)
            if (!visual) return
            visual.updateLabel(nodeLabel(node))
            const selected = node.id === p.selected, onPath = route.has(node.id), endpoint = node.id === p.pathNodes[0] || node.id === p.pathNodes.at(-1)
            const opacity = candidates.has(node.id) ? 1 : route.size && !onPath && !selected ? (candidates.size ? .45 : .22) : 1
            const d = dyn(node.id); d.base = opacity; d.hb = opacity * (selected || onPath ? .9 : .45); d.pin = selected || endpoint
            d.tint.set(onPath ? ROUTE : nodeColor(node, p.colorAxis))
            d.labelT = labelShown(node.id) ? 1 : 0
          })
          graph.linkColor((link) => pathEdges.has(link.id) ? ROUTE : p.pathEdges.length ? "#3a3643" : count > 50 ? "#4a4458" : "#5d566e")
            .linkWidth((link) => pathEdges.has(link.id) ? 4.2 : 0)
            .linkDirectionalArrowLength((link) => pathEdges.has(link.id) ? 9 : 0)
            .linkDirectionalArrowColor((link) => pathEdges.has(link.id) ? ROUTE : "#6f6685")
            .linkDirectionalParticles(routeParticles).linkDirectionalParticleSpeed(.007).linkDirectionalParticleWidth(3.4)
          host.dataset.pathEdges = JSON.stringify(graph.graphData().links.filter((link) => pathEdges.has(link.id)).map((link) => link.id))
          wake(1000)
          kick()
        }
        /** New chords unfold from the chord they connect to (or from the centre on first load) instead of popping in. */
        function arrive(ids: string[], first: boolean) {
          if (media.matches || !ids.length) return
          const fresh = new Set(ids), nodes = graph.graphData().nodes, byId = new Map(nodes.map((node) => [node.id, node])), now = performance.now()
          const edges = latest.current.graph.edges
          ids.forEach((id, index) => {
            const node = byId.get(id)
            if (!node) return
            const link = first ? undefined : edges.find((edge) => (edge.src === id && !fresh.has(edge.dst) && byId.has(edge.dst)) || (edge.dst === id && !fresh.has(edge.src) && byId.has(edge.src)))
            const origin = link ? byId.get(link.src === id ? link.dst : link.src)! : null
            arrivals.set(id, { x: origin ? origin.rx : node.rx * .12, y: origin ? origin.ry : node.ry * .12, z: origin ? origin.rz : node.rz * .12, at: now + Math.min(index, 40) * 14 })
            dyn(id).enter = 0
          })
          kick()
        }
        graph.onNodeClick((node) => latest.current.onSelect(node.id))
          .onNodeHover((node) => {
            const previous = hoveredNode
            hoveredNode = node?.id ?? ""
            const p = latest.current
            for (const id of [previous, hoveredNode]) if (visuals.has(id)) dyn(id).labelT = labelShown(id) ? 1 : 0
            host.style.cursor = node ? "pointer" : "grab"
            setHover(node ? `${nodeLabel(node)} · click to hear it` : "")
            const neighbors = new Set<string>()
            if (node) p.graph.edges.forEach((edge) => { if (edge.src === node.id) neighbors.add(edge.dst); if (edge.dst === node.id) neighbors.add(edge.src) })
            visuals.forEach((_, id) => {
              const d = dyn(id)
              d.t = id === hoveredNode ? 1 : neighbors.has(id) ? .35 : 0
              d.dimT = node && !p.pathNodes.length && id !== node.id && !neighbors.has(id) ? 1 : 0
            })
            if (node) {
              const moves = p.graph.edges.filter((edge) => edge.src === node.id).sort((a, b) => (b.prob ?? -1) - (a.prob ?? -1)).slice(0, 3)
                .map((edge) => ({ label: nodeLabel(p.graph.nodes.find((item) => item.id === edge.dst) ?? { id: edge.dst, label: edge.dst, type: "function", props: {} }), prob: edge.prob }))
              setTip({ id: node.id, label: nodeLabel(node), kind: node.type, text: functionExplanation(node.id), links: neighbors.size, moves })
              placeTip()
            } else setTip(null)
            kick(); wake()
          })
          .onLinkHover((link) => { setHover(link ? `${link.type.replaceAll("_", " ").toLowerCase()} · ${link.prob == null ? "how often is unknown" : `happens ${Math.round(link.prob * 100)}% of the time`}` : ""); wake() })
        const resize = new ResizeObserver(() => { graph.width(host.clientWidth).height(host.clientHeight); requestAnimationFrame(() => { if (!disposed) frame(performance.now()) }); wake() }); resize.observe(host)
        const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) { controls.update(); wake(1500); kick() } else { graph.pauseAnimation(); host.dataset.rendering = "paused" } }); intersection.observe(host)
        const visibility = () => { if (document.hidden) { graph.pauseAnimation(); host.dataset.rendering = "paused" } else { wake(); kick() } }; document.addEventListener("visibilitychange", visibility)
        const motionChange = () => { setReduced(media.matches); controls.enableDamping = !media.matches; refresh() }; media.addEventListener("change", motionChange)
        const contextLost = () => { setFailure("The 3D view lost its graphics connection. Your route is still available in List view."); graph.pauseAnimation() }; graph.renderer().domElement.addEventListener("webglcontextlost", contextLost)
        host.dataset.renderer = "webgl"
        performance.mark("hcg-explore-canvas-created")
        cleanup = () => {
          clearTimeout(timer); cancelAnimationFrame(raf); resize.disconnect(); intersection.disconnect()
          document.removeEventListener("visibilitychange", visibility); media.removeEventListener("change", motionChange)
          host.removeEventListener("pointermove", onPointer); host.removeEventListener("pointerdown", onPointer); host.removeEventListener("wheel", onPointer)
          controls.removeEventListener("change", onChange); controls.removeEventListener("start", onStart); controls.removeEventListener("end", onEnd)
          graph.renderer().domElement.removeEventListener("webglcontextlost", contextLost)
          delete diagnosticHost.atlasSnapshot
          releaseGPU(); visuals.clear()
        }
        runtime.current = { graph, visuals, refresh, arrive, fit, zoom, orbit, wake, dispose: cleanup }
        if (latest.current.captureRef) latest.current.captureRef.current = () => ({ positions: graph.graphData().nodes.map(({ id, rx, ry, rz }) => ({ id, x: rx, y: ry, z: rz })), camera: { position: { x: graph.camera().position.x, y: graph.camera().position.y, z: graph.camera().position.z }, target: { x: controls.target.x, y: controls.target.y, z: controls.target.z } } })
        setReady(true)
      } catch {
        if (!disposed) { cleanup(); setFailure("This device cannot start the 3D view. Open List view to explore every connection and route.") }
      }
    }
    void mount()
    return () => { disposed = true; cleanup(); runtime.current = null; if (latest.current.captureRef) latest.current.captureRef.current = null }
  }, [])

  useEffect(() => {
    const engine = runtime.current
    if (!ready || !engine) return
    const previous = engine.graph.graphData()
    const known = new Set(previous.nodes.map((node) => node.id))
    const next = atlasData(props.graph, previous.nodes)
    if (!previous.nodes.length && props.initialView) {
      const positions = new Map(props.initialView.positions.map((node) => [node.id, node]))
      next.nodes.forEach((node) => { const saved = positions.get(node.id); if (saved) { node.x = node.fx = node.rx = saved.x; node.y = node.fy = node.ry = saved.y; node.z = node.fz = node.rz = saved.z } })
    }
    const changed = next.nodes.map((node) => node.id).join("|") !== previous.nodes.map((node) => node.id).join("|") || next.links.map((link) => link.id).join("|") !== previous.links.map((link) => link.id).join("|")
    if (!changed) previous.links.forEach((link, index) => { link.prob = next.links[index].prob; link.type = next.links[index].type })
    if (changed) {
      const first = previous.nodes.length === 0
      const ids = new Set(next.nodes.map((node) => node.id))
      engine.visuals.forEach((visual, id) => { if (!ids.has(id)) { visual.dispose(); engine.visuals.delete(id) } })
      engine.graph.graphData(next)
      container.current!.dataset.positions = JSON.stringify(next.nodes.map(({ id, rx, ry, rz }) => ({ id, x: rx, y: ry, z: rz })))
      engine.arrive(next.nodes.filter((node) => !known.has(node.id)).map((node) => node.id), first)
      engine.wake()
      requestAnimationFrame(() => {
        if (runtime.current !== engine) return
        engine.refresh()
        requestAnimationFrame(() => { if (runtime.current === engine) engine.refresh() })
        if (first) {
          if (latest.current.initialView) {
            const view = latest.current.initialView, controls = engine.graph.controls() as OrbitControls
            const distance = Math.hypot(view.camera.position.x - view.camera.target.x, view.camera.position.y - view.camera.target.y, view.camera.position.z - view.camera.target.z)
            controls.maxDistance = Math.max(1400, distance * 3)
            const camera = engine.graph.camera() as PerspectiveCamera; camera.far = controls.maxDistance * 4; camera.updateProjectionMatrix()
            engine.graph.cameraPosition(view.camera.position, view.camera.target, 0); controls.update(); engine.refresh()
          } else engine.fit("reset")
          // Layout timing for performance checks: measured from the neighborhood request when one exists.
          const loaded = performance.getEntriesByName("hcg-explore-neighborhood-ready").at(-1) as PerformanceMark | undefined
          const elapsedMs = typeof loaded?.detail?.elapsedMs === "number" ? performance.now() - (loaded.startTime - loaded.detail.elapsedMs) : undefined
          performance.mark("hcg-explore-layout-complete", { detail: { elapsedMs, nodes: latest.current.graph.nodes.length } })
        }
      })
    }
    engine.refresh()
  }, [ready, props.graph, props.pathNodes, props.selected, props.initialView])

  useEffect(() => { if (ready) runtime.current?.refresh() }, [ready, props.colorAxis, props.selected, props.pathNodes, props.pathEdges, props.candidateNodes])
  // A found route can reach chords outside the current view, so bring all of it into frame once.
  const fitted = useRef(props.fitRouteKey)
  useEffect(() => {
    if (!ready || fitted.current === props.fitRouteKey) return
    fitted.current = props.fitRouteKey
    const frame = requestAnimationFrame(() => runtime.current?.fit("path"))
    return () => cancelAnimationFrame(frame)
  }, [ready, props.fitRouteKey, props.pathNodes])

  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    const engine = runtime.current
    if (!engine || event.altKey || event.ctrlKey || event.metaKey) return
    const actions: Record<string, () => void> = {
      ArrowLeft: () => engine.orbit(-.3, 0), ArrowRight: () => engine.orbit(.3, 0), ArrowUp: () => engine.orbit(0, -.18), ArrowDown: () => engine.orbit(0, .18),
      "+": () => engine.zoom(.8), "=": () => engine.zoom(.8), "-": () => engine.zoom(1.25), "0": () => engine.fit("reset"),
    }
    const action = actions[event.key]
    if (!action) return
    event.preventDefault(); action()
  }
  const disabled = !ready || !!failure
  return <div ref={stage} className={`atlas-stage${props.pathNodes.length ? " has-route" : ""}`}>
    <div className="atlas-canvas" ref={container} role="application" tabIndex={0} onKeyDown={onKey} aria-label={`3D harmonic map with ${props.graph.nodes.length} nodes and ${props.graph.edges.length} edges. Drag or use the arrow keys to look around, plus and minus to zoom. List view offers every connection as text.`} />
    {!ready && !failure && <div className="atlas-loading" role="status"><span />Unfolding the map…</div>}
    {failure && <div className="atlas-fallback" role="status"><strong>Your music is still here.</strong><p>{failure}</p><button type="button" onClick={props.onListView}>Open List view</button></div>}
    <div className="atlas-dock" role="group" aria-label="Graph camera">
      <Dock iconSize={36} iconMagnification={48} iconDistance={90} className="atlas-dock-bar">
        <DockIcon className="atlas-dock-icon"><button type="button" disabled={disabled} onClick={() => runtime.current?.zoom(.8)} aria-label="Zoom in" title="Zoom in"><Plus size={17} aria-hidden="true" /></button></DockIcon>
        <DockIcon className="atlas-dock-icon"><button type="button" disabled={disabled} onClick={() => runtime.current?.zoom(1.25)} aria-label="Zoom out" title="Zoom out"><Minus size={17} aria-hidden="true" /></button></DockIcon>
        <DockIcon className="atlas-dock-icon"><button type="button" disabled={disabled} onClick={() => runtime.current?.fit("reset")} aria-label="Recenter view" title="Recenter view"><ScanSearch size={17} aria-hidden="true" /></button></DockIcon>
        <DockIcon className="atlas-dock-icon"><button type="button" aria-label={fullScreen ? "Exit full screen" : "Full screen"} title={fullScreen ? "Exit full screen" : "Full screen"} aria-pressed={fullScreen} onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void fullscreenElement()?.requestFullscreen().catch(() => setHover("Full screen isn't available in this browser.")) }}>{fullScreen ? <Minimize2 size={16} aria-hidden="true" /> : <Maximize2 size={16} aria-hidden="true" />}</button></DockIcon>
      </Dock>
    </div>
    <div ref={tipRef} className="atlas-tip-anchor" aria-hidden="true">
      <AnimatePresence>
        {tip && <div key={tip.id} className="atlas-tip-pos"><motion.div className="atlas-tip" initial={{ opacity: 0, y: 10, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6, scale: 0.98 }} transition={{ type: "spring", stiffness: 260, damping: 26 }}>
          <div className="atlas-tip-head"><strong>{tip.label}</strong><span>{tip.kind}</span></div>
          <p>{tip.text}</p>
          {tip.moves.length > 0 && <ul>{tip.moves.map((move, index) => <li key={`${move.label}-${index}`}><span>→ {move.label}</span>{move.prob != null && <span className="atlas-tip-bar"><i style={{ width: `${Math.round(move.prob * 100)}%` }} /></span>}<b>{move.prob == null ? "—" : `${Math.round(move.prob * 100)}%`}</b></li>)}</ul>}
          <small>{tip.links} connection{tip.links === 1 ? "" : "s"} in view · click to hear it</small>
        </motion.div></div>}
      </AnimatePresence>
    </div>
    <p className="atlas-caption" data-motion={reduced ? "still" : "floating"}>{hover || "Drag to look around · scroll to zoom · distance on the map is not a similarity score"}</p>
  </div>
}
