export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && (
        <div className="mb-4 rounded-full bg-green-50 p-4">
          <Icon className="h-8 w-8 text-primary" aria-hidden="true" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-heading">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-body">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
