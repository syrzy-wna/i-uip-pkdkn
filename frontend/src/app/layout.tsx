import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "i-UIP Nerus | PKD Kuala Nerus, Terengganu",
  description:
    "Sistem Pintar Penguatkuasaan, Kertas Siasatan & Pendakwaan UIP, Pejabat Kesihatan Daerah Kuala Nerus, Terengganu (Dev: g.dev/syrzy).",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0f2744",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ms">
      <body className="min-h-screen bg-[#f4f7fb] text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
