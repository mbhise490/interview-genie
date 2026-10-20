import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <Navbar />
      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
          <Outlet />
        </div>
      </main>
      <Footer />
    </div>
  );
}
