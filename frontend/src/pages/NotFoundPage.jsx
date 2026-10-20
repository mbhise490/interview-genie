import { Link } from 'react-router-dom';
import Button from '../components/Button';
import { Home } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4 text-center">
      <h1 className="text-6xl font-bold text-primary">404</h1>
      <p className="mt-3 text-lg font-medium text-heading">Page not found</p>
      <p className="mt-1 text-sm text-body">The page you're looking for doesn't exist.</p>
      <Link to="/" className="mt-6">
        <Button>
          <Home className="h-4 w-4" aria-hidden="true" />
          Go home
        </Button>
      </Link>
    </div>
  );
}
