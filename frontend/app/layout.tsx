import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tracera',
  description: 'Website Risk Assessment Platform',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
