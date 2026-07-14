import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { Toaster } from 'react-hot-toast';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AutoWebAgent — AI Web Automation',
  description: 'Production-grade AI-powered web automation with ultra stealth anti-detection',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                borderRadius: '12px',
                background: '#1e293b',
                color: '#f8fafc',
                fontSize: '14px',
              },
            }}
          />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
