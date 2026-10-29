import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import Nav from "./nav";
import PasswordGate from "./password";

export const metadata: Metadata = {
  title: "SYNiq",
  description: "An adaptive teacher that fits the learner.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f766e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <Nav />
          <main>
            <PasswordGate>{children}</PasswordGate>
          </main>
        </SessionProvider>
      </body>
    </html>
  );
}
