import './globals.css';
import Navbar from '@/components/Navbar';
import MapPreloader from '@/components/MapPreloader';
import { ToastProvider } from '@/components/Toast';
import { AuthProvider } from '@/lib/auth';

export const metadata = {
  title: 'Tayari — Flood Early Warning',
  description:
    'Flood early warning and early action for the IGAD region. Predicts river flooding, generates multilingual advisories, and delivers alerts via SMS.',
  keywords: 'flood, early warning, IGAD, Somalia, Kenya, climate, ICPAC',
};

export const viewport = {
  themeColor: '#faf9f6',
  width: 'device-width',
  initialScale: 1,
  // Cover notches/rounded corners; we pad with env(safe-area-inset-*) in CSS.
  viewportFit: 'cover',
  // Intentionally no maximumScale/userScalable lock — pinch-zoom stays available
  // for accessibility.
};

// Resolved at build time from NEXT_PUBLIC_* env. Preconnecting to the cross-origin
// hosts the very first render depends on (map tiles + API + auth) shaves a full
// connection setup (DNS + TCP + TLS) off the critical path on slow networks.
function safeOrigin(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}
const API_ORIGIN = safeOrigin(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
const SUPABASE_ORIGIN = safeOrigin(process.env.NEXT_PUBLIC_SUPABASE_URL || '');
const TILES_ORIGIN = 'https://tiles.openfreemap.org';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />

        {/* Map tiles are the heaviest cross-origin dependency — warm the socket. */}
        <link rel="preconnect" href={TILES_ORIGIN} crossOrigin="anonymous" />
        <link rel="dns-prefetch" href={TILES_ORIGIN} />

        {API_ORIGIN && <link rel="preconnect" href={API_ORIGIN} crossOrigin="anonymous" />}
        {SUPABASE_ORIGIN && (
          <link rel="preconnect" href={SUPABASE_ORIGIN} crossOrigin="anonymous" />
        )}
      </head>
      <body>
        <AuthProvider>
          <ToastProvider>
            <div className="app-layout">
              <Navbar />
              {children}
            </div>
            <MapPreloader />
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
