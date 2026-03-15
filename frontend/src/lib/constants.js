export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4000/api';

export const customStyles = `
  :root {
    --frammer-bg: #050505;
    --frammer-panel: #111111;
    --frammer-panel-alt: #171717;
    --frammer-border: #262626;
    --frammer-copy: #f5f5f5;
    --frammer-muted: #737373;
    --frammer-accent: #ef4444;
    --frammer-accent-soft: rgba(239, 68, 68, 0.12);
  }
  @keyframes flowRight {
    0% { transform: translateX(-10px); opacity: 0; }
    50% { opacity: 1; }
    100% { transform: translateX(20px); opacity: 0; }
  }
  .dot-flow { animation: flowRight 1.5s infinite linear; }
  .dot-flow:nth-child(1) { animation-delay: 0s; }
  .dot-flow:nth-child(2) { animation-delay: 0.5s; }
  .dot-flow:nth-child(3) { animation-delay: 1.0s; }

  @keyframes tickerFlow {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
  }
  .animate-ticker { animation: tickerFlow 30s linear infinite; }
  .hide-scrollbar::-webkit-scrollbar { display: none; }
`;
