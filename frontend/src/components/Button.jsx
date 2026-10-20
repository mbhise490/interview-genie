import { Loader2 } from 'lucide-react';

const variants = {
  primary:
    'bg-primary text-white hover:bg-primary-hover active:bg-primary-active focus-ring',
  secondary:
    'bg-white text-primary border border-primary hover:bg-green-50 active:bg-green-100 focus-ring',
  danger:
    'bg-white text-red-600 border border-red-300 hover:bg-red-50 active:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2',
  ghost:
    'bg-transparent text-body hover:bg-gray-100 focus-ring',
};

export default function Button({
  children,
  variant = 'primary',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
