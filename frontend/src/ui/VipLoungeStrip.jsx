const DEFAULT_ITEMS = [
  "HIGH LIMIT",
  "PRIVATE TABLE",
  "CONCIERGE",
  "WHALE LOUNGE",
  "BLACK CARD",
  "NO TIPPING",
  "PREMIUM ONLY",
];

export default function VipLoungeStrip({ items = DEFAULT_ITEMS }) {
  const line = [...items, ...items].join("  ◆  ");

  return (
    <div className="vip-lounge-strip" aria-hidden="true">
      <div className="vip-lounge-strip__shine" />
      <div className="vip-lounge-strip__track">
        <span>{line}</span>
        <span>{line}</span>
      </div>
    </div>
  );
}
