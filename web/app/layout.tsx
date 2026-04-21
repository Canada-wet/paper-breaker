import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paper Breaker",
  description: "Daily AI paper digest, broken down for Henry.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
