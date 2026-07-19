import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "OltinChain — Proof of Reserve",
  description:
    "Live on-chain proof of reserve for OLTIN — tokenized gold minted only against attested reserves.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-background text-text-primary min-h-screen">
        {children}
      </body>
    </html>
  );
}
