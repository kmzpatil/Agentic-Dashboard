import { motion } from "framer-motion";
import { Trophy } from "lucide-react";
import GlassCard from "../GlassCard";

const champions = [
  { name: "Tech Daily", score: 98, topUser: "Alex R." },
  { name: "Gaming Hub", score: 94, topUser: "Sam T." },
  { name: "News Desk", score: 89, topUser: "Jordan M." },
];

const Screen5 = () => (
  <div className="w-full h-full flex flex-col items-center justify-center p-6">
    <motion.h2
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="text-3xl md:text-4xl font-bold text-frammer-text-pure mb-4 tracking-tighter"
    >
      The Champions
    </motion.h2>
    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="text-frammer-text-secondary text-center max-w-lg mb-10 text-balance"
    >
      A great platform needs great talent. These are your most aligned channels and your highest-potential creators.
    </motion.p>

    <div className="w-full max-w-2xl space-y-4">
      {champions.map((chan, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 + i * 0.15, type: "spring", damping: 20 }}
        >
          <GlassCard
            className={`flex items-center justify-between !p-5 md:!p-6 ${
              i === 0 ? "border-brand-primary ring-1 ring-brand-primary" : ""
            }`}
          >
            <div className="flex items-center gap-4 md:gap-6">
              <span className="text-xl md:text-2xl font-black text-frammer-text-faint w-8">#{i + 1}</span>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg md:text-xl font-bold text-frammer-text-pure">{chan.name}</h3>
                  {i === 0 && <Trophy size={18} className="text-yellow-500" />}
                </div>
                <p className="text-frammer-text-muted text-sm">
                  Top Creator: <span className="text-frammer-text-secondary font-medium">{chan.topUser}</span>
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs uppercase font-bold text-frammer-text-faint mb-1">Alignment</div>
              <div className="text-2xl font-black text-brand-primary tabular-nums">{chan.score}</div>
            </div>
          </GlassCard>
        </motion.div>
      ))}
    </div>

    <motion.p
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1 }}
      className="mt-10 text-frammer-text-muted text-sm italic text-center"
    >
      Shoutout to your top 10% of users who drove the majority of your published success!
    </motion.p>
  </div>
);

export default Screen5;
