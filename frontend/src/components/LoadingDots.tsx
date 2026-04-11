interface Props {
  color?: string;
}

export default function LoadingDots({ color = 'bg-accent' }: Props) {
  return (
    <div className="flex gap-1">
      <div className={`w-1.5 h-1.5 rounded-full ${color} animate-pulse`} />
      <div className={`w-1.5 h-1.5 rounded-full ${color} animate-pulse [animation-delay:150ms]`} />
      <div className={`w-1.5 h-1.5 rounded-full ${color} animate-pulse [animation-delay:300ms]`} />
    </div>
  );
}
