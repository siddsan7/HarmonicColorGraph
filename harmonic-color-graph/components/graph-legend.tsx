import { nodeColor } from "@/lib/graph/atlas"
export function GraphLegend({ axis, types }: { axis: string; types: string[] }) {
  return <div className="explorer-legend" aria-label="Graph encoding">{axis === "none" ? [...new Set(types)].map((type) => <span key={type}><i style={{ background: nodeColor({ id: "", label: "", type, props: {} }, "none") }} />{type}</span>) : <><span><i style={{ background: "#76d8d1" }} />Low {axis} (0–0.30)</span><span><i style={{ background: "#a995ec" }} />Middle (0.30–0.65)</span><span><i style={{ background: "#eeb980" }} />High {axis} (0.65–1)</span><span><i style={{ background: "#8290a5" }} />Unavailable</span></>}<span className="route-legend"><b aria-hidden="true">● ━▶ ●</b> Active route · ordered steps and arrows</span></div>
}
