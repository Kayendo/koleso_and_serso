import { useEffect, useState } from "react";
import { itemImageCandidates } from "../itemArt";

export default function ItemIcon({
  itemId,
  title,
  selected,
  quantity,
  charges,
  className = "",
  large = false,
}) {
  const candidates = itemImageCandidates(itemId);
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [imageOk, setImageOk] = useState(true);

  useEffect(() => {
    setCandidateIndex(0);
    setImageOk(true);
  }, [itemId]);

  const showUses =
    charges != null &&
    quantity != null &&
    (charges > quantity || (quantity === 1 && charges > 1));
  const tip = showUses ? `${title} · осталось ${charges}` : title;
  const url = candidates[candidateIndex] || null;
  const showImage = url && imageOk;

  return (
    <div
      className={[
        "inv-icon",
        large ? "inv-icon--large" : "",
        selected ? "inv-icon-selected" : "",
        showImage ? "inv-icon--has-image" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={tip}
    >
      {showImage ? (
        <img
          src={url}
          alt=""
          className="inv-icon-img"
          onError={() => {
            if (candidateIndex + 1 < candidates.length) {
              setCandidateIndex((i) => i + 1);
            } else {
              setImageOk(false);
            }
          }}
        />
      ) : (
        <span className="inv-icon-fallback" aria-hidden="true">
          {title?.trim()?.charAt(0)?.toUpperCase() || "?"}
        </span>
      )}
    </div>
  );
}
