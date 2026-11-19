import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "i-UIP Nerus | PKD Kuala Nerus, Terengganu",
  description:
    "Satu Hati, Satu Tekad: Memacu Kecemerlangan Kesihatan Kuala Nerus — Sistem Pintar Penguatkuasaan, Kertas Siasatan & Pendakwaan UIP, Pejabat Kesihatan Daerah Kuala Nerus, Terengganu (Dev: g.dev/syrzy).",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: "cover",
  themeColor: "#0f2744",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ms">
      <body className="min-h-[100dvh] overflow-x-hidden bg-[#f4f7fb] text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
