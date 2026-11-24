import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "i-UIP Nerus | Unit Inspektorat & Perundangan KKM",
  description:
    "Sistem pintar penguatkuasaan, Kertas Siasatan & pendakwaan Unit Inspektorat & Perundangan (UIP) KKM untuk Pegawai Penguat Kuasa Kesihatan Awam seluruh Malaysia (Pembangun: g.dev/syrzy).",
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
      <body className="min-h-[100dvh] overflow-x-clip bg-[#f4f7fb] text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
