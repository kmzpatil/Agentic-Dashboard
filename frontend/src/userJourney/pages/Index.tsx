import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, ChevronLeft, Share2 } from "lucide-react";
import ProgressBar from "../components/ProgressBar";
import Screen1 from "../components/screens/Screen1";
import Screen2 from "../components/screens/Screen2";
import Screen3 from "../components/screens/Screen3";
import Screen4 from "../components/screens/Screen4";
import Screen5 from "../components/screens/Screen5";
import { useToast } from "../hooks/use-toast";

const springTransition = { type: "spring" as const, damping: 25, stiffness: 120 };

const champions = [
  { name: "Tech Daily", score: 98, topUser: "Alex R." },
  { name: "Gaming Hub", score: 94, topUser: "Sam T." },
  { name: "News Desk", score: 89, topUser: "Jordan M." },
];

const screens = [Screen1, Screen2, Screen3, Screen4, Screen5];

const Index = () => {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { toast } = useToast();

  const next = () => {
    if (step < screens.length - 1) {
      setDirection(1);
      setStep(step + 1);
    }
  };

  const prev = () => {
    if (step > 0) {
      setDirection(-1);
      setStep(step - 1);
    }
  };

  const CurrentScreen = screens[step];

  return (
    <div className="fixed inset-0 bg-background overflow-hidden select-none">
      {/* Ambient glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-primary/5 rounded-full blur-[120px] pointer-events-none" />

      <ProgressBar step={step} total={screens.length} />

      <main className="relative w-full h-full">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            initial={{ x: direction > 0 ? "100%" : "-100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: direction > 0 ? "-100%" : "100%", opacity: 0 }}
            transition={springTransition}
            className="absolute inset-0"
          >
            <CurrentScreen />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Navigation */}
      <div className="fixed bottom-8 left-0 w-full px-8 flex justify-between items-center pointer-events-none z-30">
        <button
          onClick={prev}
          disabled={step === 0}
          className={`p-4 rounded-full glass-card pointer-events-auto text-frammer-text-primary transition-opacity ${
            step === 0 ? "opacity-0 pointer-events-none" : "opacity-100"
          }`}
        >
          <ChevronLeft size={20} />
        </button>

        {step === screens.length - 1 ? (
          <button className="px-8 py-4 rounded-full bg-brand-primary text-primary-foreground font-bold pointer-events-auto flex items-center gap-2 shadow-lg shadow-brand-primary/20">
            <Share2 size={18} /> Share Results
          </button>
        ) : (
          <button
            onClick={next}
            className="p-4 rounded-full bg-brand-primary text-primary-foreground pointer-events-auto shadow-lg shadow-brand-primary/20"
          >
            <ChevronRight size={20} />
          </button>
        )}
      </div>
    </div>
  );
};

export default Index;
