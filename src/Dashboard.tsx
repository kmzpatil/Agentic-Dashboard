import { useNavigate } from "react-router-dom";

function Dashboard() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: "40px" }}>
      <h1>Media Analytics Dashboard</h1>

      <button
        style={{
          background: "red",
          color: "white",
          border: "none",
          padding: "12px 20px",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "16px"
        }}
        onClick={() => navigate("/chatbot")}
      >
        Launch AI Assistant
      </button>
    </div>
  );
}

export default Dashboard;