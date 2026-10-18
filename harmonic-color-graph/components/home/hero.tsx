"use client"

import Link from "next/link"
import { motion } from "motion/react"
import { ArrowRight, ChevronDown, MessageCircle, Orbit, PenLine, Sparkles } from "lucide-react"
import { AnimatedShinyText } from "@/components/ui/animated-shiny-text"
import { BorderBeam } from "@/components/ui/border-beam"
import { ShimmerButton } from "@/components/ui/shimmer-button"
import { Constellation } from "@/components/home/constellation"
import { useReducedMotion } from "@/components/ambient/use-motion-preference"

const HEADLINE: { word: string; accent?: boolean }[] = [
  { word: "Hear" }, { word: "where" }, { word: "your" }, { word: "chords" },
  { word: "want", accent: true }, { word: "to", accent: true }, { word: "go.", accent: true },
]
const WAYS = [
  { href: "#studio", icon: PenLine, title: "Write music", text: "Sketch a progression, hear every change, keep what feels right.", scroll: true },
  { href: "/explore", icon: Orbit, title: "Explore harmony", text: "Fly through the harmonic atlas and light up routes between chords." },
  { href: "/generate", icon: Sparkles, title: "Find an idea", text: "Choose a feeling and listen to three starting progressions." },
  { href: "/assistant", icon: MessageCircle, title: "Ask the assistant", text: "Ask why a change works, with every answer tied to cited facts." },
]

function openStudio(smooth: boolean) {
  document.getElementById("studio")?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" })
  window.setTimeout(() => document.getElementById("progression-v2")?.focus({ preventScroll: true }), smooth ? 650 : 0)
}

export function HomeHero() {
  const reduced = useReducedMotion()
  return <>
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <span className="hero-pill"><AnimatedShinyText className="mx-0 max-w-none text-[.8125rem]">A harmonic atlas for songwriters</AnimatedShinyText></span>
        </motion.div>
        <h1 id="hero-title" className="hero-title display-title" aria-label="Hear where your chords want to go.">
          {HEADLINE.map(({ word, accent }, index) => <motion.span key={`${word}-${index}`} aria-hidden="true" className="hero-word"
            initial={{ opacity: 0, y: 26, filter: "blur(10px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.75, delay: 0.15 + index * 0.08, ease: [0.22, 1, 0.36, 1] }}>
            {accent ? <em>{word}</em> : word}
          </motion.span>)}
        </h1>
        <motion.p className="hero-lede" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.85 }}>
          Write a few chords and watch the music around them light up: where they tend to lead, how they feel, and the next idea worth trying. You make every musical decision.
        </motion.p>
        <motion.div className="hero-actions" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 1 }}>
          <ShimmerButton type="button" onClick={() => openStudio(!reduced)} shimmerColor="#bfeceb" background="rgba(197,216,241,.14)" borderRadius="12px" shimmerDuration="3.4s" className="hero-cta">
            <span className="hero-cta-label">Start a sketch <ArrowRight size={16} aria-hidden="true" /></span>
          </ShimmerButton>
          <Link href="/explore" className="hero-secondary">Explore the atlas <ArrowRight size={15} aria-hidden="true" /></Link>
        </motion.div>
        <motion.ul className="hero-facts" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 1.2 }}>
          <li>Deterministic harmonic analysis</li><li>Grounded in a real chord corpus</li><li>Drafts stay on your device</li>
        </motion.ul>
      </div>
      <motion.div className="hero-stage" initial={{ opacity: 0, scale: 0.96, y: 18 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.35, ease: [0.22, 1, 0.36, 1] }}>
        <Constellation />
        <BorderBeam size={220} duration={9} colorFrom="#79cfd0" colorTo="#c9b9f6" borderWidth={1.5} />
      </motion.div>
      <button type="button" className="hero-scroll" onClick={() => openStudio(!reduced)} aria-label="Scroll to the writing studio">
        <span>Start writing</span><ChevronDown size={16} aria-hidden="true" />
      </button>
    </section>
    <section className="ways" aria-label="Ways to begin">
      {WAYS.map(({ href, icon: Icon, title, text, scroll }, index) => <motion.div key={title} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.6, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}>
        {scroll
          ? <button type="button" className="way-card glass" onClick={() => openStudio(!reduced)}><Icon size={20} aria-hidden="true" /><strong>{title}</strong><span>{text}</span><ArrowRight className="way-arrow" size={16} aria-hidden="true" /></button>
          : <Link href={href} className="way-card glass"><Icon size={20} aria-hidden="true" /><strong>{title}</strong><span>{text}</span><ArrowRight className="way-arrow" size={16} aria-hidden="true" /></Link>}
      </motion.div>)}
    </section>
  </>
}
