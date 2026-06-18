import type { Metadata } from "next";
import Providers from "@/components/providers/Providers";

export const metadata: Metadata = {
  title: "Lighthouse Tools",
  description: "Gestão de ativos e templates Lighthouse",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
        />
      </head>
      <body style={{ margin: 0 }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
