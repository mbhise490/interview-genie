import { CheckCircle, XCircle, X } from 'lucide-react';

export default function Toast({ message, type = 'success', onClose }) {
  const isError = type === 'error';

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg animate-in slide-in-from-right ${
        isError
          ? 'border-red-200 bg-red-50 text-red-800'
          : 'border-green-200 bg-green-50 text-green-800'
      }`}
      role="alert"
    >
      {isError ? (
        <XCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
      ) : (
        <CheckCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
      )}
      <p className="text-sm font-medium">{message}</p>
      <button
        onClick={onClose}
        className="ml-2 shrink-0 rounded p-0.5 hover:bg-black/5"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
