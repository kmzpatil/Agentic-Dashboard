import { motion } from "framer-motion";
import { Zap } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts";
import GlassCard from "../GlassCard";

const funnelData = [
  { name: "Created", value: 14900, fill: "hsl(224, 100%, 65%)" },
  { name: "Published", value: 12200, fill: "hsl(359, 100%, 64%)" },
];

const Screen4 = () => (
  <div className="w-full h-full flex flex-col items-center justify-center p-6 md:p-8">
    <motion.div
      initial={{ opacity: 0, scaleY: 0.6 }}
      animate={{ opacity: 1, scaleY: 1 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      style={{ transformOrigin: "bottom" }}
      className="w-full max-w-3xl h-48 mb-10"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={funnelData} barGap={24}>
          <XAxis
            dataKey="name"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "hsl(0, 0%, 100%)", fontSize: 14, fontWeight: 500 }}
          />
          <YAxis hide />
          <Bar dataKey="value" radius={[8, 8, 0, 0]} barSize={90}>
            {funnelData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </motion.div>

    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
      className="w-full max-w-2xl"
    >
      <GlassCard className="border-t-4 border-t-destructive">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 rounded-full bg-destructive flex items-center justify-center">
            <Zap size={24} className="text-primary-foreground" fill="currentColor" />
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-primary-foreground">81% Conversion</h2>
        </div>
        <p className="text-secondary-foreground text-lg mb-8 text-balance">
          Your production pipeline is blazing fast. But here is your secret weapon:{" "}
          <span className="text-primary-foreground font-bold">Interview → Reels</span> yielded your highest Interaction Lift Score of the year.
        </p>
        <div className="p-4 rounded-xl bg-secondary border border-border flex justify-between items-center">
          <span className="text-muted-foreground font-medium">Lift Score</span>
          <span className="text-destructive font-black text-2xl tabular-nums">2.4x</span>
        </div>
      </GlassCard>
    </motion.div>
  </div>
);

export default Screen4;
