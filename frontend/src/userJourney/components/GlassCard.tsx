import { forwardRef, ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
}

const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(({ children, className = "" }, ref) => (
  <div ref={ref} className={`glass-card p-8 ${className}`}>
    {children}
  </div>
));

GlassCard.displayName = "GlassCard";

export default GlassCard;
