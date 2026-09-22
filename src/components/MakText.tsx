/** A readable wordmark that also respects reduced-motion preferences. */
export default function MakText({ height = 28 }: { height?: number; animated?: boolean }) {
  return <span className="owl-wordmark" style={{ fontSize: height * 0.85 }}>Mr. Owl</span>
}
