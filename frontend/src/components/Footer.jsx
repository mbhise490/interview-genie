export default function Footer() {
  return (
    <footer className="border-t border-border bg-white py-6">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <p className="text-center text-xs text-gray-400">
          &copy; {new Date().getFullYear()} Interview Genie. Built to help you ace your interviews.
        </p>
      </div>
    </footer>
  );
}
