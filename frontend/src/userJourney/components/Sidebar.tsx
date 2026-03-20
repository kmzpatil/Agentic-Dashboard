import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Activity } from "lucide-react";

const springTransition = { type: "spring" as const, damping: 25, stiffness: 120 };

interface Channel {
  name: string;
  score: number;
  topUser: string;
}

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  channels: Channel[];
}

const Sidebar = ({ isOpen, setIsOpen, channels }: SidebarProps) => (
  <>
    <button
      onClick={() => setIsOpen(true)}
      className="fixed left-6 top-1/2 -translate-y-1/2 z-40 p-3 glass-card rounded-full text-frammer-text-primary hover:text-frammer-text-pure transition-colors"
    >
      <Menu size={20} />
    </button>
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 z-40 bg-background/50"
          />
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={springTransition}
            className="fixed inset-y-0 left-0 w-72 z-50 bg-background/80 backdrop-blur-2xl border-r border-border p-8"
          >
            <div className="flex justify-between items-center mb-12">
              <span className="font-bold tracking-tighter text-xl text-brand-primary">FRAMMER AI</span>
              <button onClick={() => setIsOpen(false)} className="text-frammer-text-muted hover:text-frammer-text-pure transition-colors">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-6">
              <p className="text-frammer-text-muted text-xs uppercase tracking-widest font-semibold">Channels</p>
              {channels.map((c, i) => (
                <div key={i} className="flex items-center gap-4 group cursor-pointer">
                  <div className="w-10 h-10 rounded-xl bg-brand-blue-light border border-border flex items-center justify-center group-hover:border-brand-primary transition-colors">
                    <Activity size={16} className="text-brand-primary" />
                  </div>
                  <span className="text-frammer-text-secondary font-medium group-hover:text-frammer-text-pure transition-colors">{c.name}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  </>
);

export default Sidebar;
