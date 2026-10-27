import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Apex University — AI Academic Assistant & Student Portal",
  description: "Official student academic assistant for attendance, fees, schedules, and university regulations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-[#F8FAFC] text-slate-900 selection:bg-slate-200 selection:text-slate-900">
        {children}
      </body>
    </html>
  );
}
