"use client"

import { useEffect, useRef, useState, type RefObject } from "react"
import { Expand, Focus, HelpCircle, Maximize2, Minus, Orbit, Plus, RotateCcw, Route, Sparkles } from "lucide-react"
import type { ForceGraph3DInstance } from "3d-force-graph"
import type { Group, Sprite, Mesh, MeshBasicMaterial, SpriteMaterial, PerspectiveCamera } from "three"
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { atlasData, nodeColor, nodeLabel, type AtlasNode, type AtlasLink } from "@/lib/graph/atlas"
import type { GraphData } from "@/lib/graph/data"
import type { AtlasView } from "@/lib/graph/presentation"

type Props = { graph: GraphData; selected: string; pathNodes: string[]; pathEdges: string[]; colorAxis: string; onSelect: (id: string) => void; onListView?: () => void; initialView?: AtlasView | null; captureRef?: RefObject<(() => AtlasView) | null> }
type Atlas = ForceGraph3DInstance<AtlasNode, AtlasLink>
type NodeVisual = { group: Group; core: Mesh; halo: Sprite; ring: Sprite; label: Sprite; updateLabel: (text: string) => void; dispose: () => void }
type Runtime = { graph: Atlas; visuals: Map<string, NodeVisual>; refresh: () => void; replay: () => void; cancelReplay: () => void; fit: (mode: "all" | "path" | "selected" | "reset") => void; wake: (ms?: number) => void; dispose: () => void }
const ROUTE = "#ffd091"

export function GraphCanvas(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const runtime = useRef<Runtime | null>(null)
  const latest = useRef(props)
  const [ready, setReady] = useState(false)
  const [failure, setFailure] = useState("")
  const [hover, setHover] = useState("")
  const stage = useRef<HTMLDivElement>(null)
  const [fullScreen, setFullScreen] = useState(false)
  const [guide, setGuide] = useState(false)
  const [reduced, setReduced] = useState(false)
  useEffect(() => { latest.current = props })
  useEffect(() => { const update = () => setFullScreen(document.fullscreenElement === stage.current); document.addEventListener("fullscreenchange", update); return () => document.removeEventListener("fullscreenchange", update) }, [])

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
        controls.dampingFactor = .12
        controls.minDistance = 40
        controls.maxDistance = 1400
        controls.rotateSpeed = .65
        controls.zoomSpeed = .8
        controls.screenSpacePanning = true
        graph.renderer().setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
        graph.renderer().setClearColor(0x060a12, 0)
        graph.backgroundColor("#00000000").showNavInfo(false).numDimensions(3).enableNodeDrag(false)
          .warmupTicks(0).cooldownTicks(0).nodeLabel("").linkLabel("").linkOpacity(.8)
          .linkCurvature("curvature").linkCurveRotation("rotation").linkResolution(12)
          .linkDirectionalArrowRelPos(.79).linkDirectionalArrowResolution(12)
          .linkDirectionalParticles(0).linkDirectionalParticleWidth(1.7).linkDirectionalParticleColor(() => ROUTE).linkDirectionalParticleSpeed(.011)
        const visuals = new Map<string, NodeVisual>()
        const sphere = new THREE.SphereGeometry(3.2, 12, 8); owned.add(sphere)
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
        const ring = texture((ctx, size) => { ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(size / 2, size / 2, size * .38, 0, Math.PI * 2); ctx.stroke(); ctx.fillStyle = "#fff"; ctx.fillRect(size * .84, size / 2 - 3, 6, 6) })
        function buildNode(node: AtlasNode) {
          const existing = visuals.get(node.id)
          if (existing) return existing.group
          const group = new THREE.Group()
          const isRoute = latest.current.pathNodes.includes(node.id)
          const coreMaterial = new THREE.MeshBasicMaterial({ color: isRoute ? ROUTE : nodeColor(node, latest.current.colorAxis), transparent: true, depthTest: false, depthWrite: false })
          const core = new THREE.Mesh(sphere, coreMaterial)
          // Keep small, screen-sized points legible above crossing connections and grid lines.
          core.renderOrder = 20
          const haloMaterial = new THREE.SpriteMaterial({ map: glow, color: coreMaterial.color, transparent: true, depthWrite: false, sizeAttenuation: false, blending: THREE.AdditiveBlending })
          const halo = new THREE.Sprite(haloMaterial); halo.scale.set(32, 32, 1)
          const ringMaterial = new THREE.SpriteMaterial({ map: ring, color: ROUTE, transparent: true, depthWrite: false, sizeAttenuation: false })
          const selection = new THREE.Sprite(ringMaterial); selection.scale.set(16, 16, 1); selection.visible = node.id === latest.current.selected || node.id === latest.current.pathNodes[0] || node.id === latest.current.pathNodes.at(-1)
          const drawLabel = (ctx: CanvasRenderingContext2D, size: number, text: string) => {
            ctx.clearRect(0, 0, size, size)
            ctx.font = "500 44px Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
            ctx.shadowColor = "#060a12"; ctx.shadowBlur = 12; ctx.fillStyle = "#eef3ff"
            ctx.fillText(text, size / 2, size / 2, size - 8)
          }
          let currentLabel = nodeLabel(node)
          const labelTexture = texture((ctx, size) => drawLabel(ctx, size, currentLabel), 256)
          const labelMaterial = new THREE.SpriteMaterial({ map: labelTexture, transparent: true, depthWrite: false, sizeAttenuation: false })
          const label = new THREE.Sprite(labelMaterial); label.scale.set(.13, .13, 1); label.position.set(0, 11, 0)
          label.visible = (!latest.current.pathNodes.length && latest.current.graph.nodes.length <= 20) || node.id === latest.current.selected || isRoute
          group.add(halo, core, selection, label)
          const nodeResources = [coreMaterial, haloMaterial, ringMaterial, labelMaterial, labelTexture]
          nodeResources.forEach((resource) => owned.add(resource))
          visuals.set(node.id, { group, core, halo, ring: selection, label, updateLabel: (text) => { if (text === currentLabel) return; currentLabel = text; const canvas = labelTexture.image as HTMLCanvasElement; drawLabel(canvas.getContext("2d")!, 256, text); labelTexture.needsUpdate = true }, dispose: () => { nodeResources.forEach((resource) => { resource.dispose(); owned.delete(resource) }); group.removeFromParent() } })
          return group
        }
        graph.nodeThreeObject(buildNode)
        // Sparse guide points convey depth without inventing data or a measured similarity axis.
        const grid = new THREE.GridHelper(360, 18, 0x25354d, 0x172336)
        grid.position.y = -115
        const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]
        gridMaterials.forEach((material) => { material.transparent = true; material.opacity = .18; owned.add(material) })
        owned.add(grid.geometry); graph.scene().add(grid)
        let timer: ReturnType<typeof setTimeout> | undefined
        let visible = true
        let active = false
        const wake = (ms = 1000) => {
          if (disposed || !visible || document.hidden) return
          graph.resumeAnimation(); host.dataset.rendering = "active"
          clearTimeout(timer)
          timer = setTimeout(() => { if (!active) { graph.pauseAnimation(); host.dataset.rendering = "paused" } }, ms)
        }
        function diagnostics() {
          const position = graph.cameraPosition()
          const camera = graph.camera() as PerspectiveCamera
          camera.updateMatrixWorld()
          const scale = 82 * 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, host.clientHeight)
          const pixelScale = 2 * Math.tan(camera.fov * Math.PI / 360) / Math.max(1, host.clientHeight)
          graph.graphData().nodes.forEach((node) => {
            const visual = visuals.get(node.id)
            if (!visual) return
            const important = latest.current.selected === node.id || latest.current.pathNodes.includes(node.id)
            const depth = Math.max(1, new THREE.Vector3(node.x, node.y, node.z).applyMatrix4(camera.matrixWorldInverse).z * -1)
            visual.core.scale.setScalar(depth * pixelScale * (important ? 5 : 3.5) / 3.2)
            visual.label.scale.set(scale, scale, 1)
            visual.label.position.copy(new THREE.Vector3(0, depth * pixelScale * 17, 0).applyQuaternion(camera.quaternion))
            visual.halo.scale.setScalar(pixelScale * (important ? 44 : 32))
            visual.ring.scale.setScalar(pixelScale * 24)
          })
          host.dataset.camera = JSON.stringify(position)
          host.dataset.target = JSON.stringify(controls.target)
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
        const onChange = () => { diagnostics(); wake() }
        const onStart = () => { active = true; wake() }
        const onEnd = () => { active = false; wake() }
        controls.addEventListener("change", onChange); controls.addEventListener("start", onStart); controls.addEventListener("end", onEnd)
        const onPointer = () => wake()
        host.addEventListener("pointermove", onPointer); host.addEventListener("pointerdown", onPointer); host.addEventListener("wheel", onPointer, { passive: true })
        function fit(mode: "all" | "path" | "selected" | "reset") {
          const p = latest.current
          const nodes = graph.graphData().nodes.filter((node) => mode === "selected" ? node.id === p.selected : mode === "path" ? p.pathNodes.includes(node.id) : true)
          if (!nodes.length) return
          const center = new THREE.Vector3()
          nodes.forEach((node) => center.add(new THREE.Vector3(node.x, node.y, node.z))); center.divideScalar(nodes.length)
          const camera = graph.camera() as PerspectiveCamera
          const tangent = Math.tan(camera.fov * Math.PI / 360)
          const direction = mode === "reset" ? new THREE.Vector3(.8, .5, 1).normalize() : new THREE.Vector3().copy(camera.position).sub(controls.target).normalize()
          const right = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), direction).normalize()
          const up = new THREE.Vector3().crossVectors(direction, right).normalize()
          let distance = mode === "selected" ? 75 : 90
          nodes.forEach((node) => {
            const delta = new THREE.Vector3(node.x, node.y, node.z).sub(center)
            const depth = delta.dot(direction)
            distance = Math.max(distance, depth + Math.abs(delta.dot(right)) / (tangent * camera.aspect) * 1.3, depth + Math.abs(delta.dot(up)) / tangent * Math.max(1.5, host.clientHeight / Math.max(150, host.clientHeight - 160)))
          })
          center.addScaledVector(up, -distance * tangent * (host.clientWidth < 600 ? 110 : 65) / host.clientHeight)
          controls.maxDistance = Math.max(1400, distance * 3)
          camera.far = controls.maxDistance * 4
          camera.updateProjectionMatrix()
          const target = center.clone().addScaledVector(direction, distance)
          wake(1200); graph.cameraPosition(target, center, media.matches ? 0 : 450)
          if (media.matches) { controls.update(); graph.camera().updateMatrixWorld(); diagnostics() }
        }
        let hoveredNode = ""
        function refresh() {
          const p = latest.current, route = new Set(p.pathNodes), pathEdges = new Set(p.pathEdges)
          graph.graphData().nodes.forEach((node) => {
            const visual = visuals.get(node.id)
            if (!visual) return
            visual.updateLabel(nodeLabel(node))
            const selected = node.id === p.selected, onPath = route.has(node.id), endpoint = node.id === p.pathNodes[0] || node.id === p.pathNodes.at(-1)
            const tint = onPath ? ROUTE : nodeColor(node, p.colorAxis), opacity = route.size && !onPath && !selected ? .22 : 1
            const core = visual.core.material as MeshBasicMaterial; core.color.set(tint); core.opacity = opacity
            const halo = visual.halo.material as SpriteMaterial; halo.color.set(tint); halo.opacity = opacity * (selected || onPath ? .9 : .45)
            visual.core.scale.setScalar(endpoint ? 1.3 : selected ? 1.15 : 1)
            visual.ring.visible = selected || endpoint; (visual.ring.material as SpriteMaterial).color.set(selected ? "#e8f2ff" : ROUTE)
            visual.label.visible = (!route.size && graph.graphData().nodes.length <= 20) || selected || onPath || hoveredNode === node.id
            ;(visual.label.material as SpriteMaterial).opacity = Math.max(.3, opacity)
          })
          graph.linkColor((link) => pathEdges.has(link.id) ? ROUTE : graph.graphData().nodes.length > 50 ? "#1d2b40" : p.pathEdges.length ? "#27374c" : "#445e7c")
            .linkWidth((link) => pathEdges.has(link.id) ? 2.2 : 0)
            .linkDirectionalArrowLength((link) => pathEdges.has(link.id) ? 7.5 : 0)
            .linkDirectionalArrowColor((link) => pathEdges.has(link.id) ? ROUTE : "#445e7c")
          host.dataset.pathEdges = JSON.stringify(graph.graphData().links.filter((link) => pathEdges.has(link.id)).map((link) => link.id))
          diagnostics()
          wake()
        }
        let replayTimer: ReturnType<typeof setTimeout> | undefined
        function cancelReplay() { clearTimeout(replayTimer); graph.linkDirectionalParticles(0); host.dataset.replay = "idle"; wake() }
        function replay() {
          cancelReplay()
          if (media.matches) return
          const edges = new Set(latest.current.pathEdges)
          graph.linkDirectionalParticles((link) => edges.has(link.id) ? 1 : 0)
          host.dataset.replay = "playing"; wake(2200)
          replayTimer = setTimeout(cancelReplay, 1800)
        }
        graph.onNodeClick((node) => latest.current.onSelect(node.id))
          .onNodeHover((node) => {
            const previous = hoveredNode
            hoveredNode = node?.id ?? ""
            const p = latest.current
            // Hover changes two label sprites, never the whole link geometry.
            for (const id of [previous, hoveredNode]) {
              const visual = visuals.get(id)
              if (!visual) continue
              visual.label.visible = (!p.pathNodes.length && visuals.size <= 20) || id === p.selected || p.pathNodes.includes(id) || id === hoveredNode
              ;(visual.label.material as SpriteMaterial).opacity = 1
            }
            host.style.cursor = node ? "pointer" : "grab"
            setHover(node ? `${nodeLabel(node)} · ${node.type} · click to inspect` : "")
            wake()
          })
          .onLinkHover((link) => { setHover(link ? `${link.type.replaceAll("_", " ").toLowerCase()} · ${link.prob == null ? "Probability unavailable" : `${Math.round(link.prob * 100)}% probability`}` : ""); wake() })
        const resize = new ResizeObserver(() => { graph.width(host.clientWidth).height(host.clientHeight); requestAnimationFrame(() => { if (!disposed) diagnostics() }); wake() }); resize.observe(host)
        const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) { controls.update(); diagnostics(); wake(1500) } else { graph.pauseAnimation(); host.dataset.rendering = "paused" } }); intersection.observe(host)
        const visibility = () => { if (document.hidden) { graph.pauseAnimation(); host.dataset.rendering = "paused" } else wake() }; document.addEventListener("visibilitychange", visibility)
        const motion = () => { setReduced(media.matches); controls.enableDamping = !media.matches; cancelReplay(); wake() }; media.addEventListener("change", motion)
        const contextLost = (event: Event) => { event.preventDefault(); setFailure("The 3D view lost its graphics connection. Your route is still available in List view."); graph.pauseAnimation() }; graph.renderer().domElement.addEventListener("webglcontextlost", contextLost)
        host.dataset.renderer = "webgl"
        performance.mark("hcg-explore-canvas-created")
        cleanup = () => {
          clearTimeout(replayTimer); clearTimeout(timer); resize.disconnect(); intersection.disconnect()
          document.removeEventListener("visibilitychange", visibility); media.removeEventListener("change", motion)
          host.removeEventListener("pointermove", onPointer); host.removeEventListener("pointerdown", onPointer); host.removeEventListener("wheel", onPointer)
          controls.removeEventListener("change", onChange); controls.removeEventListener("start", onStart); controls.removeEventListener("end", onEnd)
          graph.renderer().domElement.removeEventListener("webglcontextlost", contextLost)
          delete diagnosticHost.atlasSnapshot
          releaseGPU(); visuals.clear()
        }
        runtime.current = { graph, visuals, refresh, replay, cancelReplay, fit, wake, dispose: cleanup }
        if (latest.current.captureRef) latest.current.captureRef.current = () => ({ positions: graph.graphData().nodes.map(({ id, x, y, z }) => ({ id, x, y, z })), camera: { position: { x: graph.camera().position.x, y: graph.camera().position.y, z: graph.camera().position.z }, target: { x: controls.target.x, y: controls.target.y, z: controls.target.z } } })
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
    const next = atlasData(props.graph, previous.nodes)
    if (!previous.nodes.length && props.initialView) {
      const positions = new Map(props.initialView.positions.map((node) => [node.id, node]))
      next.nodes.forEach((node) => { const saved = positions.get(node.id); if (saved) { node.x = node.fx = saved.x; node.y = node.fy = saved.y; node.z = node.fz = saved.z } })
    }
    const changed = next.nodes.map((node) => node.id).join("|") !== previous.nodes.map((node) => node.id).join("|") || next.links.map((link) => link.id).join("|") !== previous.links.map((link) => link.id).join("|")
    if (!changed) previous.links.forEach((link, index) => { link.prob = next.links[index].prob; link.type = next.links[index].type })
    if (changed) {
      const first = previous.nodes.length === 0
      const ids = new Set(next.nodes.map((node) => node.id))
      engine.visuals.forEach((visual, id) => { if (!ids.has(id)) { visual.dispose(); engine.visuals.delete(id) } })
      engine.graph.graphData(next)
      container.current!.dataset.positions = JSON.stringify(next.nodes.map(({ id, x, y, z }) => ({ id, x, y, z })))
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
          performance.mark("hcg-explore-layout-complete")
        }
      })
    }
    engine.refresh()
  }, [ready, props.graph, props.pathNodes, props.selected, props.initialView])

  useEffect(() => { if (ready) runtime.current?.refresh() }, [ready, props.colorAxis, props.selected, props.pathNodes, props.pathEdges])
  const routeIdentity = props.pathEdges.join(";")
  useEffect(() => { if (ready) runtime.current?.cancelReplay() }, [ready, routeIdentity])
  function zoom(factor: number) {
    const engine = runtime.current
    if (!engine) return
    const controls = engine.graph.controls() as OrbitControls, camera = engine.graph.camera()
    const offset = camera.position.clone().sub(controls.target)
    const distance = Math.max(controls.minDistance, Math.min(controls.maxDistance, offset.length() * factor))
    const position = offset.setLength(distance).add(controls.target)
    engine.wake(); engine.graph.cameraPosition(position, controls.target, reduced ? 0 : 350)
  }
  function orbit() {
    const engine = runtime.current
    if (!engine) return
    const controls = engine.graph.controls() as OrbitControls, position = engine.graph.camera().position.clone().sub(controls.target)
    const x = position.x, z = position.z
    position.x = x * Math.cos(.4) + z * Math.sin(.4); position.z = z * Math.cos(.4) - x * Math.sin(.4)
    position.add(controls.target); engine.wake(); engine.graph.cameraPosition(position, controls.target, reduced ? 0 : 400)
  }
  return <div ref={stage} className={`atlas-stage${props.pathNodes.length ? " has-route" : ""}`}>
    <div className="atlas-canvas" ref={container} role="img" aria-label={`3D harmonic graph with ${props.graph.nodes.length} nodes and ${props.graph.edges.length} edges. Drag to orbit. Use List view for keyboard navigation.`} />
    {!ready && !failure && <div className="atlas-loading" role="status"><span />Mapping the harmonic space…</div>}
    {failure && <div className="atlas-fallback" role="status"><strong>Your music is still here.</strong><p>{failure}</p><button type="button" onClick={props.onListView}>Open List view</button></div>}
    <div className="atlas-coordinate" aria-hidden="true"><span>HARMONIC ATLAS</span><span>RELATIONSHIP SPACE / 3D</span></div>
    <div className="atlas-axis" aria-hidden="true"><i /><i /><i /><span>x</span><span>y</span><span>z</span></div>
    <div className="atlas-toolbar" role="group" aria-label="Graph camera">
      <button type="button" disabled={!ready || !!failure} onClick={() => runtime.current?.fit("all")}><Expand size={15} />Fit graph</button>
      <button type="button" disabled={!ready || !!failure} onClick={() => runtime.current?.fit("selected")} aria-label="Focus selected"><Focus size={15} />Focus</button>
      <button type="button" disabled={!ready || !!failure} onClick={orbit}><Orbit size={15} />Orbit</button>
      <button type="button" aria-label={fullScreen ? "Exit full screen" : "Full screen"} onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void stage.current?.requestFullscreen().catch(() => setGuide(true)) }}><Maximize2 size={15} /></button>
      <span className="atlas-toolbar-divider" />
      <button type="button" disabled={!ready || !!failure} onClick={() => zoom(.8)} aria-label="Zoom in"><Plus size={16} /></button>
      <button type="button" disabled={!ready || !!failure} onClick={() => zoom(1.25)} aria-label="Zoom out"><Minus size={16} /></button>
      <button type="button" disabled={!ready || !!failure} onClick={() => runtime.current?.fit("reset")} aria-label="Reset camera"><RotateCcw size={15} /></button>
      <button type="button" aria-expanded={guide} onClick={() => setGuide(!guide)} aria-label="Graph controls guide"><HelpCircle size={16} /></button>
    </div>
    {props.pathNodes.length > 0 && <div className="atlas-route-tools"><button type="button" disabled={!ready || !!failure} onClick={() => runtime.current?.fit("path")}><Route size={14} />Fit path</button><button type="button" disabled={!ready || reduced || !!failure} onClick={() => runtime.current?.replay()} title={reduced ? "Animation disabled by reduced motion preference" : "Send a brief pulse along the route"}><Sparkles size={14} />Replay direction</button></div>}
    {guide && <div className="atlas-guide"><strong>Move through the music</strong><span>Drag to orbit · scroll / pinch to zoom</span><span>Right drag or two fingers to pan</span><span>Click a node to inspect. Focus brings it closer.</span><span>Keyboard: use the Orbit, Zoom and Focus buttons, or List view.</span></div>}
    <div className="atlas-caption"><span aria-live="polite">{hover || "Relationship layout · distance is not a similarity score"}</span><span>DRAG TO ORBIT</span></div>
  </div>
}
