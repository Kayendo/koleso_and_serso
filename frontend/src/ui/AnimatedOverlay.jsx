import { motion } from "framer-motion";

const backdrop = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.28 },
};

const panel = {
  initial: { opacity: 0, y: 28, scale: 0.96 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 16, scale: 0.98 },
  transition: { duration: 0.38, ease: [0.16, 1, 0.3, 1] },
};

export function AnimatedOverlay({
  onClose,
  className = "",
  children,
  spectate = false,
}) {
  return (
    <motion.div
      className={`overlay ${spectate ? "overlay-spectate" : ""} ${className}`.trim()}
      onClick={onClose}
      initial="initial"
      animate="animate"
      exit="exit"
      variants={backdrop}
    >
      <motion.div
        onClick={(e) => e.stopPropagation()}
        variants={panel}
        style={{ display: "contents" }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

export function AnimatedSquare({ children, className = "" }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24, scale: 0.94 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12, scale: 0.97 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
