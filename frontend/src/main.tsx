import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import VideoExplorerTable from './components/VideoExplorerTable.tsx'
// import DashboardLayout from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Notice the /* added here! */}
        <Route path="/*" element={<App />} />
        {/* <Route path="/chatbot" element={<DashboardLayout />} /> */}
      </Routes>
    </BrowserRouter>
    {/* <VideoExplorerTable/> */}
  </StrictMode>,
)