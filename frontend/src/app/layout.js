import './globals.css';
import Navbar from '@/components/Navbar';
import { ToastProvider } from '@/components/Toast';
import { AuthProvider } from '@/lib/auth';

export const metadata = {
  title: 'Tayari — Multi-Hazard Early Warning',
  description:
    'Early warning and early action for wherever you are. Tayari scores flood, earthquake, tsunami, volcanic, storm, heat, wildfire, drought and landslide risk for any location on Earth, then explains what to do in your language.',
  keywords:
    'early warning, disaster, flood, earthquake, tsunami, volcano, cyclone, heatwave, wildfire, drought, landslide, hazard alerts, climate',
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
// Empty in production, where the API is served from this origin (lib/http.js)
// and needs no preconnect.
const API_ORIGIN = safeOrigin(process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000');
const SUPABASE_ORIGIN = safeOrigin(process.env.NEXT_PUBLIC_SUPABASE_URL || '');
const TILES_ORIGIN = 'https://tiles.openfreemap.org';

// Runs before anything else on the page, so it is written in the JavaScript
// every browser since 1999 understands: no const, no arrow functions, nothing
// the oldest phone browser could choke on.
//
// Browsers that cannot run this app are sent to the simple version (/lite)
// instead of being shown a page that looks loaded but does nothing. The test is
// the floor the app is compiled for (see "browserslist" in package.json):
// ES modules, fetch, Promise and Array.prototype.flat — Chrome 69, Safari 12,
// Firefox 62. Proxy browsers (Opera Mini, UC Mini) and KaiOS feature phones go
// to /lite too: they may pass the test, but a WebGL map driven by a D-pad
// through a proxy is not a warning anyone can use.
//
// A browser that passes but still fails — an engine quirk nobody tested — is
// caught by the second half: if a script error fires and the app has not
// started (Navbar sets data-ready) after eight seconds, a banner offers /lite.
// "?full=1" skips the redirect for anyone who wants the full site regardless.
//
// It also shims globalThis (Chrome 70, Safari 12.0 lack it). Next.js ships its
// own polyfills for the other newer built-ins the bundle uses — .at(), .flat(),
// Object.fromEntries, Object.hasOwn — but not that one, and this runs before
// any bundle does.
const GATE_SCRIPT = `(function(){
var w=window,d=document,ua=navigator.userAgent||'';
if(/[?&]full=1/.test(location.search))return;
var s=d.createElement('script');
var ok=('noModule' in s)&&('fetch' in w)&&('Promise' in w)&&!!Array.prototype.flat;
var proxy=/Opera Mini|OPiOS|UCWEB|UCBrowser\\/[^ ]* ?Mini|KAIOS/i.test(ua)||!!w.operamini;
if(!ok||proxy){location.replace('/lite');return;}
if(typeof globalThis==='undefined'){w.globalThis=w;}
var failed=false;
w.addEventListener('error',function(){failed=true;},true);
setTimeout(function(){
if(d.documentElement.getAttribute('data-ready')||!failed)return;
var b=d.createElement('div');
b.setAttribute('role','alert');
b.style.cssText='position:fixed;left:0;right:0;top:0;z-index:99999;padding:12px 16px;background:#23211c;color:#fff;font:15px/1.4 sans-serif';
b.innerHTML='This page did not load properly on this browser. <a href="/lite" style="color:#fff;font-weight:bold">Open the simple version</a>';
d.body.appendChild(b);
},8000);
})();`;

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: GATE_SCRIPT }} />
        {/* JavaScript switched off: go straight to the version that needs none. */}
        <noscript
          dangerouslySetInnerHTML={{ __html: '<meta http-equiv="refresh" content="0; url=/lite">' }}
        />
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
            <a href="#main" className="skip-link">
              Skip to content
            </a>
            <noscript>
              <p className="noscript-note">
                This version of Tayari needs JavaScript.{' '}
                <a href="/lite">Use the simple version</a>, which works on any phone.
              </p>
            </noscript>
            <div className="app-layout">
              <Navbar />
              <main id="main" className="app-main">
                {children}
              </main>
            </div>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
