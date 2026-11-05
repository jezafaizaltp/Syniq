import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import Nav from "./nav";
import Offline from "./offline";
import PasswordGate from "./password";

// Font files live in app/fonts (SIL Open Font License, from Google Fonts), so builds never
// depend on reaching Google and the fonts also work offline. See app/fonts/README.md.
const body = localFont({
  src: [
    { path: "./fonts/atkinson-hyperlegible-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/atkinson-hyperlegible-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-body",
  display: "swap",
});
const head = localFont({
  src: [
    { path: "./fonts/fraunces.woff2", weight: "500 700", style: "normal" },
    { path: "./fonts/fraunces-italic.woff2", weight: "500 700", style: "italic" },
  ],
  variable: "--font-head",
  display: "swap",
});
const easy = localFont({ src: "./fonts/lexend.woff2", weight: "100 900", variable: "--font-easy", display: "swap" });

export const metadata: Metadata = {
  title: "SYNiq",
  description: "An adaptive teacher that fits the learner.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#a63d2a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${body.variable} ${head.variable} ${easy.variable}`}>
      <body>
        <SessionProvider>
          <Nav />
          <Offline />
          <main>
            <PasswordGate>{children}</PasswordGate>
          </main>
        </SessionProvider>
      </body>
    </html>
  );
}
