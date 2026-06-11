/** Золотой VIP-бейдж — казино, high limit, private table. */
export default function VipChip({
  label = "VIP",
  variant = "gold",
  className = "",
  pulse = false,
}) {
  return (
    <span
      className={[
        "vip-chip",
        `vip-chip--${variant}`,
        pulse ? "vip-chip--pulse" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {label}
    </span>
  );
}
