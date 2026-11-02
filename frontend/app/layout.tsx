import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible, Fraunces, Lexend } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import Nav from "./nav";
import Offline from "./offline";
import PasswordGate from "./password";

// Fonts are bundled with the app at build time, so they also work offline.
const body = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-body", display: "swap" });
const head = Fraunces({ subsets: ["latin"], weight: ["500", "600", "700"], style: ["normal", "italic"], variable: "--font-head", display: "swap" });
const easy = Lexend({ subsets: ["latin"], variable: "--font-easy", display: "swap" });

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
