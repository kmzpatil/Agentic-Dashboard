import { motion } from "framer-motion";

interface ProgressBarProps {
  step: number;
  total: number;
}

const ProgressBar = ({ step, total }: ProgressBarProps) => (
  <div className="fixed top-0 left-0 w-full h-1.5 flex gap-1 z-50 px-2 pt-2">
    {[...Array(total)].map((_, i) => (
      <div key={i} className="flex-1 h-full bg-frammer-text-faintest rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-brand-primary"
          initial={{ width: 0 }}
          animate={{ width: i <= step ? "100%" : "0%" }}
          transition={{ duration: 0.5 }}
        />
      </div>
    ))}
  </div>
);

export default ProgressBar;
