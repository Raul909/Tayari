import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import Navbar from '@/components/Navbar';
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
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body>
        <AuthProvider>
          <ToastProvider>
            <div className="app-layout">
              <Navbar />
              {children}
            </div>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
