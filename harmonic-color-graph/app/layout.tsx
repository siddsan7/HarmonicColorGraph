import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AmbientBackdrop } from "@/components/ambient/backdrop";
import { MotionProvider } from "@/components/ambient/motion-provider";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

// Display face: an editorial serif that gives headlines the warmth of a printed score
// and pairs cleanly with Geist for interface text.
const display = Instrument_Serif({
  variable: "--font-display",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Harmonic Color Graph", template: "%s · Harmonic Color Graph" },
  description: "Key-aware harmonic analysis, functional Roman numerals, and grounded relationship evidence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${display.variable} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col"><MotionProvider><TooltipProvider delayDuration={120}><AmbientBackdrop /><Suspense fallback={children}><AppShell>{children}</AppShell></Suspense></TooltipProvider></MotionProvider></body>
    </html>
  );
}
