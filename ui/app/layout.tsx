import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Knowledge Assistant | Engineering Onboarding',
  description: 'Enterprise Retrieval-Augmented Generation for Internal Technical Knowledge',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
