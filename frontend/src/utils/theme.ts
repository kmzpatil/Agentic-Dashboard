export const T = {
  bg: "#050505",       // Deep black background
  surface: "#111111",  // Slightly lighter black for panels/cards
  border: "#262626",   // Dark gray borders
  text: "#ffffff",     // Pure white text
  muted: "#a3a3a3",    // Gray text for secondary info
  faint: "#525252",    // Darker gray for inactive elements
  accent: "#e00000",   // Bold red
  danger: "#ef4444",   // Lighter red for errors
};

export const PALETTE: Record<string, string> = { 
  red: "#e00000", 
  white: "#ffffff", 
  gray: "#737373", 
  darkgray: "#404040" 
};

export const MULTI: string[] = ["#e00000", "#ffffff", "#a3a3a3", "#525252", "#991b1b"];

export const scheme = (s: string, i: number = 0): string => 
  s === "multi" ? MULTI[i % MULTI.length] : (PALETTE[s] || T.accent);