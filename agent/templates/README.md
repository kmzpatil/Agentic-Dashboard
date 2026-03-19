# Frontend Templates

This directory houses the frontend templates that provide the graphical interface for the Frammer Analytics engine. The primary file here is `index.html`, which serves as a lightweight but highly capable Single Page Application (SPA) dashboard. 

## `index.html` Overview

The `index.html` file acts as the primary user-facing viewport. It allows end-users to type natural-language questions, sends those requests to the backend API (`/api/query`), and dynamically renders artificial-intelligence-orchestrated dashboard arrays on the fly. 

It handles everything from API state management to XML parsing and graphing without the need for a complex JavaScript frontend framework.

### Key Architectural Traits
* **Zero-Build Vanilla Stack:** The interface is built purely using HTML, CSS (using native CSS custom properties for a robust dark mode), and Vanilla JavaScript. Charting is powered by `Chart.js` injected via CDN.
* **Component-Driven XML Parsing:** The interface doesn't just display static data; it acts as a layout interpreter. When the backend AI returns an XML representation string defining the logical structure of a dashboard (e.g., rows containing KPI nodes or Line Chart nodes), `renderDashboard()` consumes that XML to dynamically assemble the DOM array.
* **State & Asynchrony:** Centralized in the `submitQuery()` function, the script elegantly handles loading bounds, HTTP POSTing to the agent backend, and distributing the response. It tears down old charts, clears canvases, and pipes incoming relational datasets into fresh Chart.js instances.

### UI Components
The user interface is broken down into four distinct, conditionally-rendered functional areas:
1. **The Query Bar:** At the top of the interface, providing input for ad-hoc questioning alongside several click-to-fill example "chips."
2. **The SQL Pill (`#sql-section`):** A transparent trace box exposing the actual SQL query the AI formulated based on the user's prompt. 
3. **The Layout Engine (`#dashboard`):** Maps logical `Widget` components parsed from the XML definition to actual visual containers (`kpi-card` and `chart-card`).
4. **Insights Board (`#insights-section`):** Renders AI-driven executive summaries and textual takeaways interpreting the graphical data above it.

This robust template serves as the final, humanized bridge between the Model Context Protocol queries executing beneath the hood and the visually-oriented humans reading the output.
