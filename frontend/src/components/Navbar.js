'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import UserMenu from '@/components/UserMenu';

export default function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Dashboard' },
    { href: '/alerts', label: 'Alerts' },
    { href: '/report', label: 'Report' },
  ];

  return (
    <nav className="navbar">
      <Link href="/" className="navbar-brand">
        <div className="navbar-title">Tayari</div>
        <div className="navbar-subtitle">Flood Early Warning</div>
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
        <a 
          href="mailto:contact@launchpixel.in?subject=Tayari Bug Report / Feedback" 
          className="nav-link feedback-link"
          title="Provide feedback or report a bug"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          💬 <span className="feedback-text">Feedback</span>
        </a>
        <UserMenu />
      </div>
    </nav>
  );
}
