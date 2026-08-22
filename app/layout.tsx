import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAP Reconciliation",
  description: "Procurement intelligence and three-way matching",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
