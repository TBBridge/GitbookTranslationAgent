import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { APP_NAME } from "@/lib/constants";

export const metadata: Metadata = {
  title: APP_NAME,
  description: "Control plane for local GitBook translation workers."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="app-shell">{children}</main>
      </body>
    </html>
  );
}
