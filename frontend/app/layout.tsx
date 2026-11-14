import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AstroGuard | Space Systems Intelligence",
  description: "Independent space-systems intelligence and mission observability platform.",
  applicationName: "AstroGuard",
  keywords: ["AstroGuard", "space systems", "mission control", "telemetry", "anomaly intelligence"]
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}