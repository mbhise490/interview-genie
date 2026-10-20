import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { BrainCircuit, LogOut, LayoutDashboard, PlusCircle } from 'lucide-react';

const navLinks = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/new-interview', label: 'New Interview', icon: PlusCircle },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 font-semibold text-heading">
          <BrainCircuit className="h-6 w-6 text-primary" aria-hidden="true" />
          <span className="hidden sm:inline">Interview Genie</span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-green-50 text-primary'
                    : 'text-body hover:bg-gray-50 hover:text-heading'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User + Logout */}
        <div className="flex items-center gap-3">
          {user && (
            <span className="hidden text-sm text-body md:inline">
              {user.username}
            </span>
          )}
          <button
            onClick={logout}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-body hover:bg-gray-50 hover:text-heading transition-colors focus-ring"
            aria-label="Log out"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
