import { motion } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer, CartesianGrid } from "recharts";
import { Heart, MessageCircle, Share2 } from "lucide-react";
import { useEffect, useState } from "react";
import GlassCard from "../GlassCard";

const cdfData = [
  { month: "Jan", uploaded: 1000, created: 950, published: 800 },
  { month: "Apr", uploaded: 4500, created: 4300, published: 3500 },
  { month: "Jul", uploaded: 8000, created: 7800, published: 6200 },
  { month: "Oct", uploaded: 13000, created: 12500, published: 10500 },
  { month: "Dec", uploaded: 15420, created: 14900, published: 12200 },
];

const engagement = { likes: "1.2M", comments: "85K", shares: "450K" };

const emojis = ["❤️", "💬", "🔁", "🔥"];

interface FloatingEmoji {
  id: number;
  emoji: string;
  x: number;
  size: number;
  duration: number;
  delay: number;
}

const generateEmojis = (): FloatingEmoji[] =>
  Array.from({ length: 18 }, (_, i) => ({
    id: i,
    emoji: emojis[Math.floor(Math.random() * emojis.length)],
    x: Math.random() * 100,
    size: 16 + Math.random() * 24,
    duration: 3 + Math.random() * 3,
    delay: Math.random() * 2,
  }));

const Screen1 = () => {
  const [floatingEmojis, setFloatingEmojis] = useState<FloatingEmoji[]>([]);

  useEffect(() => {
    setFloatingEmojis(generateEmojis());
  }, []);

  return (
    <div className="relative w-full h-full flex items-end justify-center pb-28 px-6 overflow-hidden">
      {/* Background Chart */}
      <div className="absolute inset-0 opacity-40">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={cdfData}>
            <defs>
              <linearGradient id="colorUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(224, 100%, 65%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(224, 100%, 65%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(359, 100%, 64%)" stopOpacity={0.25} />
                <stop offset="95%" stopColor="hsl(359, 100%, 64%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorPublished" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(0, 0%, 100%)" stopOpacity={0.1} />
                <stop offset="95%" stopColor="hsl(0, 0%, 100%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <Area type="natural" dataKey="uploaded" stroke="hsl(224, 100%, 65%)" fill="url(#colorUp)" strokeWidth={3} />
            <Area type="natural" dataKey="created" stroke="hsl(359, 100%, 64%)" fill="url(#colorCreated)" strokeWidth={2} strokeDasharray="5 5" />
            <Area type="natural" dataKey="published" stroke="hsla(0, 0%, 100%, 0.25)" fill="url(#colorPublished)" strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Floating Emojis */}
      {floatingEmojis.map((e) => (
        <motion.div
          key={e.id}
          initial={{ y: "100vh", opacity: 0 }}
          animate={{ y: "-20vh", opacity: [0, 1, 1, 0] }}
          transition={{ duration: e.duration, delay: e.delay, ease: "easeOut" }}
          className="absolute pointer-events-none"
          style={{ left: `${e.x}%`, fontSize: e.size }}
        >
          {e.emoji}
        </motion.div>
      ))}

      {/* Content Card */}
      <GlassCard className="max-w-2xl w-full relative z-10">
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-destructive font-bold tracking-widest text-xs uppercase mb-4 block"
        >
          The Momentum
        </motion.span>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-5xl md:text-7xl font-bold text-primary-foreground tracking-tighter mb-6 tabular-nums"
        >
          15,420
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-secondary-foreground text-lg leading-relaxed mb-6 text-balance"
        >
          This year, your content engine never stopped. You hit the ground running and finished the year with a massive archive of assets.
        </motion.p>

        {/* Engagement Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="flex items-center gap-6 mb-6"
        >
          <div className="flex items-center gap-2">
            <Heart size={16} className="text-destructive" />
            <span className="text-primary-foreground font-semibold">{engagement.likes}</span>
            <span className="text-muted-foreground text-sm">Likes</span>
          </div>
          <div className="flex items-center gap-2">
            <MessageCircle size={16} className="text-primary" />
            <span className="text-primary-foreground font-semibold">{engagement.comments}</span>
            <span className="text-muted-foreground text-sm">Comments</span>
          </div>
          <div className="flex items-center gap-2">
            <Share2 size={16} className="text-muted-foreground" />
            <span className="text-primary-foreground font-semibold">{engagement.shares}</span>
            <span className="text-muted-foreground text-sm">Shares</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8 }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-destructive rounded-full text-primary-foreground font-bold text-sm"
        >
          🔥 Usage spiked by +42% in October
        </motion.div>
      </GlassCard>
    </div>
  );
};

export default Screen1;
