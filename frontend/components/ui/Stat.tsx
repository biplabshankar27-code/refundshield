export function Stat({
  value,
  label,
  tone = "text",
}: {
  value: string;
  label: string;
  tone?: "text" | "primary" | "danger" | "accent";
}) {
  const tones = {
    text: "text-text",
    primary: "text-primary",
    danger: "text-danger",
    accent: "text-accent",
  } as const;
  return (
    <div className="space-y-1">
      <div className={`font-mono text-2xl font-semibold ${tones[tone]}`}>
        {value}
      </div>
      <div className="text-[11px] uppercase tracking-widest text-text/50">
        {label}
      </div>
    </div>
  );
}
