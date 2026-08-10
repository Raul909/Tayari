'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserMenu from '@/components/UserMenu';
import FeedbackModal from '@/components/FeedbackModal';

// "Basins" is gone from here on purpose. A river basin is flood-only hydrology
// jargon, and having it as a top-level destination in a nine-hazard product
// told the wrong story about what this is — someone worried about an earthquake
// had no way in. The eight calibrated rivers now live under the flood hazard,
// which is what they are a detail of.
//
// Icons are for the mobile tab bar only; the desktop bar stays text-only.
const LINKS = [
  { href: '/', label: 'My area', short: 'Area', icon: '📍' },
  { href: '/hazards', label: 'Hazards', short: 'Hazards', icon: '⚠️' },
  { href: '/alerts', label: 'Alerts', short: 'Alerts', icon: '🔔' },
  { href: '/report', label: 'Report', short: 'Report', icon: '📸' },
];

/**
 * Top bar on desktop, top bar plus a bottom tab bar on phones.
 *
 * Four destinations, a feedback button and an account menu do not fit across a
 * 360 px phone: the row needed roughly 430 px, so flex squeezed every item and
 * the labels clipped mid-word. Scrolling the bar sideways would have hidden
 * destinations behind a gesture nobody would think to make.
 *
 * So on small screens navigation moves to a fixed bottom tab bar — thumb-
 * reachable, the standard pattern on both mobile platforms — and the top bar
 * keeps only the brand and the account controls. Nothing is hidden and nothing
 * is truncated.
 */
export default function Navbar() {
  const [showFeedback, setShowFeedback] = useState(false);
  const pathname = usePathname();

  const isActive = (href) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <>
      <nav className="navbar">
        <Link href="/" className="navbar-brand">
          <div className="navbar-title">Tayari</div>
          <div className="navbar-subtitle">Multi-Hazard Early Warning</div>
        </Link>

        <div className="navbar-nav">
          <div className="navbar-links">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${isActive(link.href) ? 'active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <button
            onClick={() => setShowFeedback(true)}
            className="nav-link feedback-link"
            title="Provide feedback or report a bug"
            aria-label="Provide feedback"
          >
            <span aria-hidden="true">💬</span>
            <span className="feedback-text">Feedback</span>
          </button>
          <UserMenu />
        </div>

        {showFeedback && <FeedbackModal onClose={() => setShowFeedback(false)} />}
      </nav>

      {/* Phone navigation. Hidden above 768px, where the top bar has room. */}
      <nav className="tabbar" aria-label="Main">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`tabbar-item ${isActive(link.href) ? 'active' : ''}`}
            aria-current={isActive(link.href) ? 'page' : undefined}
          >
            <span className="tabbar-icon" aria-hidden="true">{link.icon}</span>
            <span className="tabbar-label">{link.short}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
