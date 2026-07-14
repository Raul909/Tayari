import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';
import Navbar from '@/components/Navbar';

export const metadata = {
  title: 'Tayari — AI Flood Early Warning System',
  description:
    'AI-powered flood early warning and early action system for the IGAD region. Predicts river flooding, generates multilingual advisories, and delivers alerts via SMS.',
  keywords: 'flood, early warning, IGAD, Somalia, Kenya, AI, climate, ICPAC',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#0A1628" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body>
        <div className="app-layout">
          <Navbar />
          {children}
        </div>
      </body>
    </html>
  );
}
