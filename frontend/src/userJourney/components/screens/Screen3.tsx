import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

const distribution = [
  { name: "Instagram", value: 50, fill: "#ff4649" },
  { name: "YouTube", value: 30, fill: "#4d77ff" },
  { name: "TikTok", value: 20, fill: "#ffffff" },
];

const Screen3 = () => (
  <div className="w-full h-full flex flex-col items-center justify-center p-6">
    <div className="relative w-full max-w-md h-[340px] md:h-[400px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={distribution}
            innerRadius="55%"
            outerRadius="75%"
            paddingAngle={6}
            dataKey="value"
            stroke="none"
            animationBegin={200}
            animationDuration={1200}
          >
            {distribution.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-12">
        <span className="text-frammer-text-muted text-xs uppercase tracking-[0.2em] mb-2">Personality</span>
        <motion.h3
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}
          className="text-2xl md:text-3xl font-bold text-frammer-text-pure leading-tight text-balance"
        >
          Omnichannel Explorer
        </motion.h3>
      </div>
    </div>

    <div className="flex gap-6 mt-4 mb-8">
      {distribution.map((d, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.fill }} />
          <span className="text-frammer-text-muted">{d.name}</span>
        </div>
      ))}
    </div>

    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.8 }}
      className="text-center max-w-xl"
    >
      <div className="text-5xl font-black text-brand-primary mb-4 tabular-nums">
        9.4<span className="text-xl text-frammer-text-faint">/10</span>
      </div>
      <p className="text-xs uppercase tracking-widest text-frammer-text-muted font-bold mb-3">Content Diversity Score</p>
      <p className="text-frammer-text-secondary text-lg text-balance">
        Your Content Diversity Score is off the charts, successfully distributing your message across multiple platforms.
      </p>
    </motion.div>
  </div>
);

export default Screen3;
