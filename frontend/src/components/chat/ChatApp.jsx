import { useState, useEffect, useRef } from 'react';
import Sidebar from '../layout/Sidebar';
import ChatHeader from './ChatHeader';
import ChatContainer from './ChatContainer';
import Composer from './Composer';
import AnalyticsPanel from '../analytics/AnalyticsPanel';
import { useAuth } from '../../contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

function ChatApp() {
  const [sessionId, setSessionId] = useState('default');
  const [messages, setMessages] = useState([]);
  const [datasetContext, setDatasetContext] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const chatContainerRef = useRef(null);
  const { refreshAccessToken } = useAuth();

  const getAuthHeaders = async () => {
    let accessToken = localStorage.getItem('accessToken');
    if (!accessToken) return {};
    
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      if (Date.now() >= payload.exp * 1000) {
        accessToken = await refreshAccessToken();
      }
    } catch (e) {
      accessToken = await refreshAccessToken();
    }
    
    return accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {};
  };

  const fetchSessions = async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/sessions`, { headers });
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const startNewSession = () => {
    const newId = `session_${Date.now()}`;
    setSessionId(newId);
    setMessages([]);
    setDatasetContext(null);
    setShowAnalytics(false);
  };

  const loadSession = async (id) => {
    setSessionId(id);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/sessions/${id}`, { headers });
      const data = await response.json();
      setMessages(data.messages || []);
      setDatasetContext(data.dataset_context || null);
    } catch (error) {
      console.error('Error loading session:', error);
    }
  };

  const renameSession = async (id, newTitle) => {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${API_BASE}/sessions/${id}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({ title: newTitle })
      });
      fetchSessions();
    } catch (error) {
      console.error('Error renaming session:', error);
    }
  };

  const deleteSession = async (id) => {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${API_BASE}/sessions/${id}/delete`, { method: 'DELETE', headers });
      if (id === sessionId) {
        startNewSession();
      }
      fetchSessions();
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const handleSendMessage = async (text) => {
    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...headers 
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId
        })
      });

      const data = await response.json();
      const aiMsg = { role: 'assistant', content: data.response };
      setMessages(prev => [...prev, aiMsg]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    setLoading(true);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { ...headers },
        body: formData
      });
      const data = await response.json();

      if (!response.ok) {
        const errorMsg = data.error || data.detail || `Error ${response.status}`;
        setMessages(prev => [...prev, { role: 'assistant', content: `Error al analizar el archivo: ${errorMsg}` }]);
        return;
      }

      setDatasetContext(data);
      const aiMsg = { role: 'assistant', content: data.response || 'Archivo procesado.' };
      setMessages([aiMsg]);
      setShowAnalytics(true);
      fetchSessions();
    } catch (error) {
      console.error('Error analyzing file:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error de red al analizar el archivo. Verifica tu conexión.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt) => {
    if (!datasetContext) {
      handleSendMessage(prompt);
    } else {
      handleSendMessage(prompt);
    }
  };

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <div className="app-shell">
      <div className="void-fog" aria-hidden="true">
        <div className="fog-node fn-1"></div>
        <div className="fog-node fn-2"></div>
        <div className="fog-node fn-3"></div>
      </div>

      <div className={`app-container ${showAnalytics ? 'show-analytics' : ''}`}>
        <Sidebar
          sessions={sessions}
          currentSessionId={sessionId}
          datasetContext={datasetContext}
          onNewSession={startNewSession}
          onLoadSession={loadSession}
          onRenameSession={renameSession}
          onDeleteSession={deleteSession}
        />

        <main className="chat-main">
          <ChatHeader
            showAnalytics={showAnalytics}
            onToggleAnalytics={() => setShowAnalytics(!showAnalytics)}
          />

          <div className="chat-stage">
            <div className="chat-container" ref={chatContainerRef}>
              <ChatContainer
                messages={messages}
                loading={loading}
                datasetContext={datasetContext}
                onPromptClick={handlePromptClick}
              />
            </div>
          </div>

          <Composer
            onSendMessage={handleSendMessage}
            onFileUpload={handleFileUpload}
          />
        </main>

        {showAnalytics && datasetContext && (
          <AnalyticsPanel
            datasetContext={datasetContext}
            onClose={() => setShowAnalytics(false)}
          />
        )}
      </div>
    </div>
  );
}

export default ChatApp;
