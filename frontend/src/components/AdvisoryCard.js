'use client';

import { useState, useEffect } from 'react';
import { sendChatMessage } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function AdvisoryCard({ advisory, basinId, role, language }) {
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [messagesRemaining, setMessagesRemaining] = useState(5);
  const { user } = useAuth();

  useEffect(() => {
    // Reset chat when advisory changes
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessages([]);
    setChatOpen(false);
    setMessagesRemaining(5);
    setInputValue('');
  }, [advisory, basinId, role, language]);

  if (!advisory) return null;

  const level = advisory.risk_level?.toLowerCase() || 'low';

  async function handleSend(e) {
    e.preventDefault();
    if (!inputValue.trim() || sending || messagesRemaining <= 0) return;
    
    const newMsg = { role: 'user', content: inputValue.trim() };
    const currentSession = [...messages];
    setMessages([...currentSession, newMsg]);
    setInputValue('');
    setSending(true);

    try {
      const res = await sendChatMessage(basinId, newMsg.content, role, language, currentSession, user?.id);
      setMessages([...currentSession, newMsg, { role: 'ai', content: res.reply }]);
      setMessagesRemaining(res.messages_remaining);
    } catch (err) {
      setMessages([...currentSession, newMsg, { role: 'ai', content: 'Sorry, failed to get a response.' }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={`advisory-card advisory-card--${level}`}>
      <div className="advisory-title">{advisory.title}</div>
      <div className="advisory-body">{advisory.body}</div>
      {advisory.actions && advisory.actions.length > 0 && (
        <ul className="advisory-actions">
          {advisory.actions.map((action, i) => (
            <li key={i}>{action}</li>
          ))}
        </ul>
      )}
      {advisory.ai_generated && (
        <div className="advisory-ai-note">
          ✨ AI-generated advisory — AI can make mistakes. Verify critical details
          with official sources before acting.
        </div>
      )}
      
      <button 
        className="advisory-chat-toggle"
        onClick={() => setChatOpen(!chatOpen)}
      >
        💬 {chatOpen ? 'Hide chat' : 'Ask about this advisory'}
      </button>

      {chatOpen && (
        <div className="advisory-chat">
          <div className="chat-thread">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-bubble chat-bubble--${msg.role}`}>
                {msg.content}
              </div>
            ))}
            {sending && (
              <div className="chat-bubble chat-bubble--ai" style={{ opacity: 0.7 }}>
                Thinking...
              </div>
            )}
          </div>
          
          <form className="chat-input-row" onSubmit={handleSend}>
            <input 
              type="text" 
              placeholder="Ask a question..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={sending || messagesRemaining <= 0}
            />
            <button 
              type="submit" 
              className="btn btn-primary btn-sm"
              disabled={sending || messagesRemaining <= 0 || !inputValue.trim()}
            >
              Send
            </button>
          </form>
          <div className="chat-remaining">
            {messagesRemaining} of 5 questions remaining
          </div>
        </div>
      )}
    </div>
  );
}
