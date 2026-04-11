interface Props {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export default function Card({ title, children, className = '' }: Props) {
  return (
    <div className={`bg-surface-alt rounded-xl border border-border p-4 ${className}`}>
      {title && (
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide mb-3">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}
