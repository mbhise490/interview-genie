import { Loader2 } from 'lucide-react';

export default function Loader({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-16" role="status">
      <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
      <p className="mt-3 text-sm text-body">{message}</p>
    </div>
  );
}
