import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { AppToaster } from "@/components/toaster";
import { CommandMenu } from "@/components/command-menu";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const serif = Instrument_Serif({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#09090b",
};

export const metadata: Metadata = {
  title: {
    default: "Aegis Beta — Security assessments for AI agents",
    template: "%s · Aegis Beta",
  },
  description:
    "Aegis runs controlled adversarial assessments against AI agents, using industry sandboxes with synthetic data and permissioned tools, and keeps the evidence for regression and reporting.",
  openGraph: {
    title: "Aegis Beta — Security assessments for AI agents",
    description: "Controlled adversarial testing, industry sandboxes, and regression evidence for AI agents.",
    type: "website",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable} ${serif.variable} h-full`}>
      <body className="min-h-full antialiased">
        {children}
        <CommandMenu />
        <AppToaster />
      </body>
    </html>
  );
}
