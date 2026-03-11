import React from "react";

// ════════════════════════════════════════════════════════════════
//  TYPES & INTERFACES
// ════════════════════════════════════════════════════════════════

export interface ChatMessage {
  role: "user" | "agent";
  text: string;
  xml?: string;
  isErr?: boolean;
}

export interface ParsedXML {
  meta?: { title: string; description: string };
  rows?: Array<{
    id: string | null;
    label: string;
    widgets: Record<string, string>[];
  }>;
  notice?: string | null;
  error?: string;
}

export interface WidgetProps {
  a: Record<string, string>;
}

export interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
}

// ════════════════════════════════════════════════════════════════
//  GLOBAL DATA STORE
// ════════════════════════════════════════════════════════════════

// We export this as a const object so widgets can read from it synchronously
export const DATA_STORE: Record<string, any> = {};

// Helper function to update the store safely across modules
export function updateDataStore(newData: Record<string, any>) {
  // Clear existing keys
  for (const key in DATA_STORE) {
    delete DATA_STORE[key];
  }
  // Assign new keys
  Object.assign(DATA_STORE, newData);
}

// ════════════════════════════════════════════════════════════════
//  MASTER XML
// ════════════════════════════════════════════════════════════════

export const MASTER_XML: string = `<dashboard version="1.0" theme="dark" cols="12">
  <meta>
    <title>Live Media Analytics</title>
    <description>Use Agent Chat to generate charts from backend data</description>
    <created>2026-03-09</created>
    <notice message="No sample CSV is loaded. Run a query to populate dashboard data." />
  </meta>
  <layout></layout>
</dashboard>`;