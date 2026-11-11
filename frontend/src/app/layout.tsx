import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "YottaFlex VoC Intelligence | Enterprise Analytics",
  description:
    "Next.js Frontend separated from FastAPI Backend & SQLite/SQLAlchemy Database for multi-channel Voice of Customer analytics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

