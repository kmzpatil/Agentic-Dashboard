import React from "react";
import {  Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./sidebar/Sidebar";
import InteractiveDashboard from "./pages/dynamic/InteractiveDashboard";
import StaticDashboard from "./pages/static/StaticDashboard";
import { T } from "./utils/theme";

export default function App() {
  return (
    <>
      {/* Global CSS Reset */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        body { font-family: 'Inter', 'Segoe UI', sans-serif; background: ${T.bg}; color: ${T.text}; overflow: hidden; }
        ::-webkit-scrollbar{width:6px;height:6px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
        ::-webkit-scrollbar-thumb:hover{background:#525252}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
      `}</style>

      <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
        {/* Persistent Global Sidebar */}
        <Sidebar />
        
        {/* Dynamic Page Content */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dynamic" replace />} />
            <Route path="/dynamic" element={<InteractiveDashboard />} />
            <Route path="/static" element={<StaticDashboard />} />
            {/* Add more routes here as your app grows */}
          </Routes>
        </div>
      </div>
    </>
  );
}