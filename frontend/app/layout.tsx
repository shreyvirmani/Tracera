import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tracera - Defensive Website Risk Assessment',
  description: 'Analyze website security configuration and risk posture',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}