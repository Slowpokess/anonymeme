/**
 * 🏗️ Root Layout для Next.js App Router
 * Production-ready layout с провайдерами и глобальными настройками
 */

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin', 'cyrillic'] })

export const metadata: Metadata = {
  title: 'Anonymeme - Anonymous Memecoin Trading',
  description: 'Trade memecoins anonymously on Solana blockchain. Create, trade, and earn with the next generation of decentralized finance.',
  keywords: 'solana, memecoin, trading, defi, cryptocurrency, anonymous, blockchain',
  authors: [{ name: 'Anonymeme Team' }],
  creator: 'Anonymeme',
  publisher: 'Anonymeme',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  openGraph: {
    title: 'Anonymeme - Anonymous Memecoin Trading',
    description: 'Trade memecoins anonymously on Solana blockchain',
    url: '/',
    siteName: 'Anonymeme',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Anonymeme - Anonymous Memecoin Trading',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Anonymeme - Anonymous Memecoin Trading',
    description: 'Trade memecoins anonymously on Solana blockchain',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    // google: 'google-verification-code',
    // yandex: 'yandex-verification-code',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <Providers>
          <div id="__next">
            {children}
          </div>
        </Providers>
        
        {/* Portals */}
        <div id="modal-root" />
        <div id="tooltip-root" />
        <div id="dropdown-root" />
      </body>
    </html>
  )
}