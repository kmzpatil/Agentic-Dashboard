from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import uvicorn
import xml.etree.ElementTree as ET

# Import the exact chat turn function from your main agent
# This leverages Ollama and the SQL/XML pipeline together!
from master_agent import run_chat_turn, DEFAULT_OLLAMA_MODEL, AgentState

app = FastAPI()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Analytics Chat</title>
    <!-- Include Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #0f172a;
            --chat-bg: #1e293b;
            --text-color: #f8fafc;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --border: #334155;
            --user-msg: #3b82f6;
            --bot-msg: #334155;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        header {
            background-color: var(--chat-bg);
            padding: 1.5rem;
            text-align: center;
            border-bottom: 1px solid var(--border);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 10;
        }
        
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            background: linear-gradient(90deg, #60a5fa, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            max-width: 1000px;
            margin: 0 auto;
            width: 100%;
        }
        
        .message {
            max-width: 85%;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            line-height: 1.5;
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            background-color: var(--user-msg);
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        
        .bot-message {
            background-color: var(--bot-msg);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            width: 100%;
        }
        
        .chart-container {
            margin-top: 1.5rem;
            background: #0f172a;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #334155;
            height: 350px;
            width: 100%;
        }
        
        .xml-toggle {
            margin-top: 1rem;
            background: rgba(255,255,255,0.1);
            border: none;
            color: #94a3b8;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        
        .xml-container {
            display: none;
            background-color: #0d1117;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
            overflow-x: auto;
            border: 1px solid #30363d;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.8rem;
            white-space: pre-wrap;
            color: #e6edf3;
        }
        
        .xml-tag { color: #7ee787; }
        .xml-text { color: #a5d6ff; }
        
        .input-area {
            background-color: var(--chat-bg);
            padding: 1.5rem;
            border-top: 1px solid var(--border);
        }
        
        .input-form {
            display: flex;
            gap: 1rem;
            max-width: 1000px;
            margin: 0 auto;
            width: 100%;
        }
        
        input {
            flex: 1;
            padding: 1rem 1.5rem;
            border-radius: 9999px;
            border: 1px solid var(--border);
            background-color: var(--bg-color);
            color: var(--text-color);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        
        input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }
        
        button {
            padding: 0 2rem;
            border-radius: 9999px;
            border: none;
            background-color: var(--accent);
            color: white;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
        }
        
        button:hover {
            background-color: var(--accent-hover);
        }
        
        button:active {
            transform: scale(0.98);
        }
        
        .loading {
            display: none;
            align-self: flex-start;
            margin-bottom: 1.5rem;
        }
        
        .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: var(--text-color);
            border-radius: 50%;
            margin-right: 4px;
            animation: bounce 1.4s infinite ease-in-out both;
        }
        
        .dot:nth-child(1) { animation-delay: -0.32s; }
        .dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <header>
        <h1>Agent Analytics Chat</h1>
    </header>
    
    <div class="chat-container" id="chat-container">
        <div class="message bot-message">
            Hi! I am the analytics agent! You can ask me questions like <strong>"published vs created conversion"</strong>. I will reply with an LLM response and render the chart!
        </div>
    </div>
    
    <div class="loading" id="loading">
        <div class="message bot-message" style="display: flex; align-items: center; padding: 1rem 1.5rem; border-radius: 9999px; width: auto;">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    </div>
    
    <div class="input-area">
        <form class="input-form" id="chat-form">
            <input type="text" id="query-input" placeholder="Ask about analytics data..." required autocomplete="off">
            <button type="submit">Ask Agent</button>
        </form>
    </div>

    <script>
        let chartIdCounter = 0;
        
        // Simple XML formatter for visual output
        function formatXml(xml) {
            let formatted = '';
            let pad = 0;
            xml = xml.replace(/(>)(<)(\/*)/g, '$1\\r\\n$2$3');
            xml.split('\\r\\n').forEach(node => {
                let indent = 0;
                if (node.match(/.+<\\/\\w[^>]*>$/)) {
                    indent = 0;
                } else if (node.match(/^<\\/\\w/)) {
                    if (pad != 0) { pad -= 1; }
                } else if (node.match(/^<\\w[^>]*[^\\/]>.*$/)) {
                    indent = 1;
                } else {
                    indent = 0;
                }
                
                let padding = '';
                for (let i = 0; i < pad; i++) { padding += '  '; }
                formatted += padding + node + '\\r\\n';
                pad += indent;
            });
            
            return formatted
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/(&lt;[\\/a-zA-Z0-9_-]+&gt;)/g, '<span class="xml-tag">$1</span>')
                .replace(/(>)([^<]+)(<)/g, '$1<span class="xml-text">$2</span>$3');
        }
        
        // Parse the raw XML into a Javascript Chart.js config object
        function renderChartFromXml(xmlString, canvasId) {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlString, "text/xml");
            
            // Check parsing errors
            if (xmlDoc.getElementsByTagName("parsererror").length > 0) {
                console.error("XML Parsing Error");
                return;
            }
            
            const intentNode = xmlDoc.querySelector("intent");
            const intent = intentNode ? intentNode.textContent : "";
            
            const chartTypeNode = xmlDoc.querySelector("chart_type");
            let llmChartType = chartTypeNode ? chartTypeNode.textContent.trim().toLowerCase() : "";
            
            const items = xmlDoc.querySelectorAll("data > item");
            if (items.length === 0) return; // No data to chart
            
            let labels = [];
            let datasets = [];
            let chartType = 'bar'; // default format
            
            // Very basic auto-charting logic based on intent
            if (intent === "publishing_funnel") {
                chartType = 'line';
                let processedArr = [];
                let publishedArr = [];
                let uploadedArr = [];
                
                items.forEach(item => {
                    labels.push(item.querySelector("month").textContent);
                    uploadedArr.push(Number(item.querySelector("uploaded_count")?.textContent || 0));
                    processedArr.push(Number(item.querySelector("processed_count")?.textContent || 0));
                    publishedArr.push(Number(item.querySelector("published_count")?.textContent || 0));
                });
                
                datasets = [
                    {
                        label: 'Uploaded Video Count',
                        data: uploadedArr,
                        backgroundColor: 'rgba(255, 206, 86, 0.5)',
                        borderColor: 'rgba(255, 206, 86, 1)',
                        borderWidth: 2,
                        tension: 0.3
                    },
                    {
                        label: 'Processed (Created) Video Count',
                        data: processedArr,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 2,
                        tension: 0.3
                    },
                    {
                        label: 'Published Video Count',
                        data: publishedArr,
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 2,
                        tension: 0.3
                    }
                ];
            } else if (intent === "input_type_mix") {
                chartType = 'bar'; // Stacked bar works best for multiple categories per channel
                let datasetMap = {};
                
                items.forEach(item => {
                    labels.push(item.querySelector("channel")?.textContent || 'Unknown');
                    
                    // Iterate through children to find categories
                    Array.from(item.children).forEach(child => {
                        let tag = child.tagName;
                        if (tag !== 'channel') {
                            if (!datasetMap[tag]) {
                                datasetMap[tag] = [];
                            }
                            datasetMap[tag].push(Number(child.textContent || 0));
                        }
                    });
                });
                
                // Color palette for dynamic categories
                const colors = [
                    'rgba(255, 99, 132, 0.7)', 'rgba(54, 162, 235, 0.7)', 
                    'rgba(255, 206, 86, 0.7)', 'rgba(75, 192, 192, 0.7)', 
                    'rgba(153, 102, 255, 0.7)', 'rgba(255, 159, 64, 0.7)'
                ];
                
                let i = 0;
                for (const [key, dataArr] of Object.entries(datasetMap)) {
                     datasets.push({
                         label: key.replace(/_/g, ' '),
                         data: dataArr,
                         backgroundColor: colors[i % colors.length]
                     });
                     i++;
                }

            } else {
                 // Fallback chart charting the first numeric value
                chartType = (['bar', 'line', 'pie', 'doughnut'].includes(llmChartType)) ? llmChartType : 'bar';
                let firstNumField = null;
                items.forEach((item, index) => {
                    let labelNode = item.children[0]; // Assume first column is label
                    labels.push(labelNode ? labelNode.textContent : `Record ${index+1}`);
                    
                    Array.from(item.children).forEach(child => {
                        let val = Number(child.textContent);
                        if (!isNaN(val) && val > 0 && !firstNumField) {
                             firstNumField = child.tagName;
                        }
                    });
                });
                
                if (firstNumField) {
                     let dataArr = [];
                     items.forEach(item => {
                          let foundNode = item.querySelector(firstNumField);
                          dataArr.push(foundNode ? Number(foundNode.textContent) : 0);
                     });
                     
                     // Generate dynamic colors for pie pieces
                     const bgColors = dataArr.map((_, i) => `hsl(${(i * 360) / dataArr.length}, 70%, 50%)`);
                     
                     datasets = [{
                          label: firstNumField,
                          data: dataArr,
                          backgroundColor: bgColors,
                          borderColor: '#0f172a',
                          borderWidth: 2
                     }];
                }

            }
            
            // Generate distinct charting options based on type
            let chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                color: '#e2e8f0',
                plugins: {
                    legend: { labels: { color: '#e2e8f0' } }
                }
            };
            
            if (chartType === 'bar' || chartType === 'line') {
                chartOptions.scales = {
                    y: { 
                        beginAtZero: true, 
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: '#e2e8f0' }
                    },
                    x: { 
                        grid: { color: 'rgba(255,255,255,0.1)' },
                        ticks: { color: '#e2e8f0' }
                    }
                };
            }
            
            // Build the actual chart
            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, {
                type: chartType,
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: chartOptions
            });
        }

        const chatForm = document.getElementById('chat-form');
        const queryInput = document.getElementById('query-input');
        const chatContainer = document.getElementById('chat-container');
        const loading = document.getElementById('loading');
        
        let chatHistory = [];

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const query = queryInput.value.trim();
            if (!query) return;
            
            // Add user message
            const userMsg = document.createElement('div');
            userMsg.className = 'message user-message';
            userMsg.textContent = query;
            chatContainer.appendChild(userMsg);
            
            queryInput.value = '';
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Show loading
            loading.style.display = 'block';
            chatContainer.appendChild(loading);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, history: chatHistory })
                });
                
                const data = await response.json();
                
                // Hide loading
                loading.style.display = 'none';
                document.body.appendChild(loading);
                
                // Add Assistant text
                const botMsg = document.createElement('div');
                botMsg.className = 'message bot-message';
                
                let htmlContent = `<p>${data.message}</p>`;
                
                // If the backend sent XML logic, chart it!
                if (data.chart_xml && data.chart_xml.length > 10) {
                    chartIdCounter++;
                    const cid = "chart_" + chartIdCounter;
                    const xmlId = "xml_" + chartIdCounter;
                    
                    htmlContent += `
                        <div class="chart-container">
                            <canvas id="${cid}"></canvas>
                        </div>
                        <button class="xml-toggle" onclick="document.getElementById('${xmlId}').style.display = document.getElementById('${xmlId}').style.display === 'block' ? 'none' : 'block'">Toggle Raw XML Payload</button>
                        <div class="xml-container" id="${xmlId}">${formatXml(data.chart_xml)}</div>
                    `;
                    
                    botMsg.innerHTML = htmlContent;
                    chatContainer.appendChild(botMsg);
                    
                    // Render AFTER appending so the DOM has the exact Canvas ID
                    setTimeout(() => {
                        renderChartFromXml(data.chart_xml, cid);
                    }, 50);
                } else {
                    botMsg.innerHTML = htmlContent;
                    chatContainer.appendChild(botMsg);
                }
                
                // Ensure scroll captures full chart
                setTimeout(() => chatContainer.scrollTop = chatContainer.scrollHeight, 100);
                
                // Manage history manually
                chatHistory.push({ user: query, assistant: data.message });
                if (chatHistory.length > 6) chatHistory.shift();
                
            } catch (error) {
                loading.style.display = 'none';
                document.body.appendChild(loading);
                
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message bot-message';
                errorMsg.innerHTML = `<strong>Error:</strong> Failed to fetch agent response. Is Ollama running?`;
                chatContainer.appendChild(errorMsg);
            }
        });
    </script>
</body>
</html>
"""

class ChatRequest(BaseModel):
    query: str
    history: list = []

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTML_TEMPLATE

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # Calls the master agent logic (requires Ollama to be running on 11434!)
        state = AgentState(messages=req.history, current_model=DEFAULT_OLLAMA_MODEL)
        result = run_chat_turn(
            user_question=req.query,
            state=state
        )
        return {
            "message": result.get("message", "No message generated."),
            "chart_xml": result.get("chart", "")
        }
    except Exception as e:
        return {"message": f"Error fulfilling request: {str(e)}", "chart_xml": ""}

if __name__ == "__main__":
    print("Starting chat web UI on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
