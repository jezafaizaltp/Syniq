import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import Nav from "./nav";

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
          <main>{children}</main>
        </SessionProvider>
      </body>
    </html>
  );
}
