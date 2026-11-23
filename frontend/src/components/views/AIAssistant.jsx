import React, { useState } from "react";
import { Send, Trash2, Bot, User } from "lucide-react";
import { apiService } from "../../services/apiService";

const SAMPLE_PROMPTS = [
  "What is the current AQI?",
  "What are the effects of PM2.5?",
  "What precautions should I take?",
  "Explain the difference between PM2.5 and PM10."
];

export function AIAssistant({ selectedLocation }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      text: `Hello! Ask me anything about air quality in ${selectedLocation}, particulate pollutants, or health precautions.`
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSend = async (promptText) => {
    const question = (promptText ?? input).trim();
    if (!question || loading) return;

    const userMsg = { id: `u-${Date.now()}`, role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await apiService.sendChatMessage(question, selectedLocation);
      const botMsg = {
        id: `a-${Date.now()}`,
        role: "assistant",
        text: res.data?.answer || "No response returned."
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setError(err.message || "Failed to retrieve assistant response.");
    } finally {
      setLoading(false);
    }
  };

  const clearConversation = () => {
    setError(null);
    setMessages([
      {
        id: `reset-${Date.now()}`,
        role: "assistant",
        text: `Conversation cleared. Ready for environmental questions regarding ${selectedLocation}.`
      }
    ]);
  };

  return (
    <div className="view-stack">
      <section className="card chat-container">
        <div className="section-header">
          <div>
            <h3>Environmental Knowledge Assistant</h3>
            <span className="muted-text">Context Location: {selectedLocation}</span>
          </div>
          <button type="button" className="btn btn-secondary" onClick={clearConversation}>
            <Trash2 size={15} />
            <span>Clear Conversation</span>
          </button>
        </div>

        <div className="prompt-chips">
          {SAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="chip-btn"
              onClick={() => handleSend(prompt)}
              disabled={loading}
            >
              {prompt}
            </button>
          ))}
        </div>

        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-bubble-row ${msg.role}`}>
              <div className="chat-avatar">
                {msg.role === "assistant" ? <Bot size={16} /> : <User size={16} />}
              </div>
              <div className="chat-bubble">{msg.text}</div>
            </div>
          ))}
          {loading && (
            <div className="chat-bubble-row assistant">
              <div className="chat-avatar">
                <Bot size={16} />
              </div>
              <div className="chat-bubble typing">Retrieving environmental knowledge...</div>
            </div>
          )}
        </div>

        {error && <div className="inline-error">{error}</div>}

        <form
          className="chat-input-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
            type="text"
            placeholder="Ask an environmental or air quality question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
            <Send size={16} />
            <span>Send</span>
          </button>
        </form>
      </section>
    </div>
  );
}