import { motion } from "framer-motion";
import { Target } from "lucide-react";
import GlassCard from "../GlassCard";

const Screen2 = () => {
  const efficiency = 85;
  const cdas = 92;
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (efficiency / 100) * circumference;

  return (
    <div className="w-full h-full flex flex-col md:flex-row items-center justify-center gap-12 p-8 md:p-12">
      <div className="relative w-56 h-56 md:w-80 md:h-80 flex-shrink-0">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 200 200">
          <circle cx="100" cy="100" r={radius} fill="transparent" stroke="hsl(0 0% 100% / 0.06)" strokeWidth="12" />
          <motion.circle
            cx="100" cy="100" r={radius} fill="transparent" stroke="#4d77ff"
            strokeWidth="12" strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <motion.span
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.8, type: "spring" }}
            className="text-5xl md:text-6xl font-black text-frammer-text-pure tabular-nums"
          >
            {efficiency}%
          </motion.span>
          <span className="text-frammer-text-muted text-xs uppercase tracking-widest font-bold mt-1">Efficiency</span>
        </div>
      </div>
      <div className="max-w-md space-y-8">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-3xl md:text-4xl font-bold tracking-tight text-frammer-text-pure text-balance"
        >
          The Efficiency Engine
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-frammer-text-secondary leading-relaxed"
        >
          Your average published video is significantly shorter than your created videos. You are mastering the art of the hook! Your Clip Duration Alignment shows incredible precision.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
          <GlassCard className="!p-6 flex items-center gap-6">
            <div className="p-4 bg-brand-blue-light rounded-2xl">
              <Target className="text-brand-primary" />
            </div>
            <div>
              <p className="text-frammer-text-muted text-xs uppercase font-bold">Precision Score (CDAS)</p>
              <p className="text-2xl font-bold text-frammer-text-primary tabular-nums">{cdas}</p>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
};

export default Screen2;
