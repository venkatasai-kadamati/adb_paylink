import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'PayLink — money, connected.', description: 'A simulated peer-to-peer banking experience for CS 5600. No real money.' };
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
