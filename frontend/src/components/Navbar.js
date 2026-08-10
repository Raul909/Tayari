'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserMenu from '@/components/UserMenu';
import FeedbackModal from '@/components/FeedbackModal';

export default function Navbar() {
  const [showFeedback, setShowFeedback] = useState(false);
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Hazards' },
    // The eight calibrated flood basins keep their own entry rather than being
    // folded into the location view: their thresholds are tuned against real
    // historical floods, which makes them a genuinely different — and better —
    // answer for the places they cover.
    { href: '/basins', label: 'Basins' },
    { href: '/alerts', label: 'Alerts' },
    { href: '/report', label: 'Report' },
  ];

  return (
    <nav className="navbar">
      <Link href="/" className="navbar-brand">
        <div className="navbar-title">Tayari</div>
        <div className="navbar-subtitle">Multi-Hazard Early Warning</div>
      </Link>

      <div className="navbar-nav">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`nav-link ${pathname === link.href ? 'active' : ''}`}
          >
            {link.label}
          </Link>
        ))}
        <button 
          onClick={() => setShowFeedback(true)}
          className="nav-link feedback-link"
          title="Provide feedback or report a bug"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit', color: 'inherit' }}
        >
          💬 <span className="feedback-text">Feedback</span>
        </button>
        <UserMenu />
      </div>
      
      {showFeedback && (
        <FeedbackModal onClose={() => setShowFeedback(false)} />
      )}
    </nav>
  );
}
