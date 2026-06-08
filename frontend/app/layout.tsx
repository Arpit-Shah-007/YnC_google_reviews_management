import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Y&C Review Hub',
  description: 'Yum & Chill Restaurant Group — Google Review Analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
