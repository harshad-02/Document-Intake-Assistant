import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
// @ts-ignore
import html2pdf from 'html2pdf.js';
import personImg from './assets/person.png';
import asstentImg from './assets/asstent.png';
import startImg from './assets/start.png';
import chatImg from './assets/chat.png';
import previewImg from './assets/preview.png';
import fieldsImg from './assets/fields.png';
import copyImg from './assets/copy.png';
import editImg from './assets/edit.png';
import downloadImg from './assets/download.png';
import { DocumentTemplate } from './DocumentTemplate';
import { EditPanel } from './EditPanel';
import {
  createSession,
  getSession,
  sendMessage,
  editField,
  editBatchField,
  resetSession,
  getHealth,
  ApiClientError,
  type SessionResponse,
  type StateSnapshot,
  type MessageInfo,
  type FieldSnapshot,
} from './api';
import './App.css';

// ── Field metadata ───────────────────────────────────────────────────────────

const FIELD_ORDER = [
  'full_name',
  'home_address',
  'covers_worldwide_assets',
  'has_children',
  'children',
  'executor_name',
  'executor_relationship',
  'specific_gifts',
  'additional_wishes',
] as const;

type FieldName = (typeof FIELD_ORDER)[number];

const FIELD_LABELS: Record<FieldName, string> = {
  full_name: 'Full Name',
  home_address: 'Home Address',
  covers_worldwide_assets: 'Worldwide Assets',
  has_children: 'Has Children',
  children: 'Children',
  executor_name: 'Executor Name',
  executor_relationship: 'Executor Relationship',
  specific_gifts: 'Specific Gifts',
  additional_wishes: 'Additional Wishes',
};

const BOOLEAN_FIELDS: FieldName[] = ['covers_worldwide_assets', 'has_children'];
const LIST_FIELDS: FieldName[] = ['children', 'specific_gifts', 'additional_wishes'];

function formatFieldValue(field: FieldSnapshot): string {
  if (field.status === 'unknown' || field.value == null) return '—';
  if (typeof field.value === 'boolean') return field.value ? 'Yes' : 'No';
  if (Array.isArray(field.value)) {
    if (field.value.length === 0) return 'None specified';
    return field.value.join(', ');
  }
  if (typeof field.value === 'object' && field.value !== null) {
    if ('worldwide' in (field.value as any)) {
      const w = field.value as any;
      if (w.worldwide) return 'Worldwide';
      if (w.specific) return w.region ? `Specific: ${w.region}` : 'Specific region only';
      return '—';
    }
  }
  return String(field.value);
}

// ── Main App ─────────────────────────────────────────────────────────────────

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<StateSnapshot | null>(null);
  const [document, setDocument] = useState('');
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const isSendingRef = useRef(false);
  const [notifications, setNotifications] = useState<
    { id: number; type: 'warning' | 'error'; text: string }[]
  >([]);
  const [editingField, setEditingField] = useState<FieldName | null>(null);
  const [editValue, setEditValue] = useState('');
  const [activeTab, setActiveTab] = useState<'chat' | 'state' | 'document'>('chat');
  const [provider, setProvider] = useState('mock');
  const [currentPath, setCurrentPath] = useState(window.location.pathname);

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const notifIdRef = useRef(0);

  // ── Notifications ────────────────────────────────────────────────────────

  const addNotification = useCallback(
    (type: 'warning' | 'error', text: string) => {
      const id = ++notifIdRef.current;
      setNotifications((prev) => [...prev, { id, type, text }]);
      setTimeout(() => {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      }, 6000);
    },
    []
  );

  const dismissNotification = (id: number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  // ── Auto-scroll ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTo({
        top: chatScrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, isSending]);

  useEffect(() => {
    if (!isSending) {
      setTimeout(() => inputRef.current?.focus({ preventScroll: true }), 10);
    }
  }, [isSending, activeTab]);

  // ── Init session & Routing ────────────────────────────────────────────────

  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  useEffect(() => {
    initSession();
  }, []);

  async function initSession() {
    setIsLoading(true);
    try {
      // Check health
      try {
        const health = await getHealth();
        setProvider(health.provider);
      } catch {
        // ignore health check failure
      }

      // Try to restore existing session
      const savedId = localStorage.getItem('session_id');
      if (savedId) {
        try {
          const data = await getSession(savedId);
          applySession(data);
          setIsLoading(false);
          return;
        } catch {
          localStorage.removeItem('session_id');
        }
      }

      // Create new session
      const data = await createSession();
      applySession(data);
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      } else {
        addNotification('error', 'Failed to connect to the server.');
      }
    } finally {
      setIsLoading(false);
    }
  }

  function applySession(data: SessionResponse) {
    setSessionId(data.id);
    setState(data.state);
    setDocument(data.document);

    if (data.messages.length === 1 && data.messages[0].role === 'assistant') {
      setMessages([]);
      setIsSending(true);
      setTimeout(() => {
        setMessages(data.messages);
        setIsSending(false);
      }, 1500);
    } else {
      setMessages(data.messages);
    }

    setMissingFields(data.missing_fields);
    localStorage.setItem('session_id', data.id);
  }

  // ── Send message ─────────────────────────────────────────────────────────

  async function handleSend() {
    if (!inputText.trim() || !sessionId || isSendingRef.current) return;

    const msg = inputText.trim();
    setInputText('');
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setIsSending(true);
    isSendingRef.current = true;

    try {
      const result = await sendMessage(sessionId, msg);
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply }]);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);

      if (result.missing_fields.length === 0 && missingFields.length > 0) {
        setTimeout(() => {
          handleDownloadDoc();
        }, 1000);
      }

      if (result.warnings?.length > 0) {
        result.warnings.forEach((w) => addNotification('warning', w));
      }
    } catch (err: any) {
      if (err && typeof err === 'object' && 'code' in err) {
        if (err.code === 'SESSION_NOT_FOUND') {
          addNotification('error', 'Session expired. Starting a new one…');
          localStorage.removeItem('session_id');
          initSession();
        } else {
          addNotification('error', err.message || 'Unknown API error');
          // Remove the optimistic user message since the call failed
        }
      } else {
        addNotification('error', err instanceof Error ? err.message : 'Failed to send message.');
      }
    } finally {
      setIsSending(false);
      isSendingRef.current = false;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // ── Direct edit ──────────────────────────────────────────────────────────

  async function handleEditSave(fieldName: FieldName) {
    if (!sessionId) return;

    let parsedValue: unknown = editValue;

    if (BOOLEAN_FIELDS.includes(fieldName)) {
      parsedValue = editValue === 'true';
    } else if (LIST_FIELDS.includes(fieldName)) {
      parsedValue = editValue
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    }

    try {
      const result = await editField(sessionId, fieldName, parsedValue);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);
      if (result.warnings?.length > 0) {
        result.warnings.forEach((w) => addNotification('warning', w));
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      }
    }
    setEditingField(null);
    setEditValue('');
  }

  async function handleClearField(fieldName: FieldName) {
    if (!sessionId) return;
    try {
      const result = await editField(sessionId, fieldName, null);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      }
    }
  }

  async function handleFieldEdit(fieldName: string, value: any) {
    if (!sessionId) return;
    try {
      // If it's a list field, split by commas and trim
      let processedValue = value;
      if (LIST_FIELDS.includes(fieldName as FieldName) && typeof value === 'string') {
        processedValue = value.split(',').map(s => s.trim()).filter(Boolean);
      }
      
      const result = await editField(sessionId, fieldName, processedValue);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);
      if (result.warnings?.length > 0) {
        result.warnings.forEach((w) => addNotification('warning', w));
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      }
    }
  }

  async function handleBatchEdit(updates: Record<string, any>) {
    if (!sessionId) return;
    try {
      // Pre-process list fields
      const processedUpdates = { ...updates };
      for (const [key, value] of Object.entries(processedUpdates)) {
        if (LIST_FIELDS.includes(key as FieldName) && typeof value === 'string') {
          processedUpdates[key] = value.split(',').map(s => s.trim()).filter(Boolean);
        }
      }
      
      const result = await editBatchField(sessionId, processedUpdates);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);
      if (result.missing_fields.length === 0 && missingFields.length > 0) {
        setTimeout(() => {
          handleDownloadDoc();
        }, 1000);
      }
      if (result.warnings?.length > 0) {
        result.warnings.forEach((w) => addNotification('warning', w));
      }
      
      // Fetch latest messages since the assistant might have generated a new question based on the edit
      try {
        const sessionData = await getSession(sessionId);
        setMessages(sessionData.messages);
      } catch (e) {
        console.error("Failed to refresh messages after edit", e);
      }

      addNotification('success', 'Document updated successfully!');
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      }
    }
  }

  async function handleBooleanEdit(fieldName: FieldName, value: boolean) {
    if (!sessionId) return;
    try {
      const result = await editField(sessionId, fieldName, value);
      setState(result.state);
      setDocument(result.document);
      setMissingFields(result.missing_fields);
      if (result.warnings?.length > 0) {
        result.warnings.forEach((w) => addNotification('warning', w));
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        addNotification('error', err.message);
      }
    }
    setEditingField(null);
  }

  // ── Reset ────────────────────────────────────────────────────────────────

  async function handleReset() {
    if (!sessionId) return;
    try {
      const data = await resetSession(sessionId);
      applySession(data);
      setCurrentPath('/chat');
    } catch {
      // If reset fails, create a new session
      try {
        const data = await createSession();
        applySession(data);
        setCurrentPath('/chat');
      } catch (err) {
        if (err instanceof ApiClientError) {
          addNotification('error', err.message);
        }
      }
    }
  }

  // ── Copy/Download document ───────────────────────────────────────────────

  function handleCopyDoc() {
    navigator.clipboard.writeText(document);
    addNotification('warning', 'Document copied to clipboard!');
  }

  function handleDownloadDoc() {
    const element = window.document.querySelector('.document-content');
    if (!element) return;

    const htmlEl = window.document.documentElement;

    // Temporarily remove zoom so html2canvas calculates text metrics correctly
    const originalZoom = htmlEl.style.zoom;
    htmlEl.style.zoom = '1';

    // Ensure the element is not clipped by scroll containers
    const originalMaxHeight = (element as HTMLElement).style.maxHeight;
    const originalOverflow = (element as HTMLElement).style.overflow;
    (element as HTMLElement).style.maxHeight = 'none';
    (element as HTMLElement).style.overflow = 'visible';

    const opt = {
      margin: 0.5,
      filename: 'personal-wishes-document.pdf',
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' },
      pagebreak: { mode: ['css', 'legacy'] }
    };

    html2pdf().set(opt).from(element).save().then(() => {
      // Restore original styles
      (element as HTMLElement).style.maxHeight = originalMaxHeight;
      (element as HTMLElement).style.overflow = originalOverflow;
      // Restore zoom
      htmlEl.style.zoom = originalZoom;
    });
  }

  // ── Progress calculation ─────────────────────────────────────────────────

  function getProgress(): { confirmed: number; total: number } {
    if (!state) return { confirmed: 0, total: 9 };

    const noChildren =
      state.has_children.status === 'confirmed' && state.has_children.value === false;

    let total = noChildren ? 8 : 9;
    let confirmed = 0;

    for (const fn of FIELD_ORDER) {
      if (fn === 'children' && noChildren) continue;
      const f = state[fn];
      if (f.status === 'confirmed') confirmed++;
    }

    return { confirmed, total };
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner" />
      </div>
    );
  }

  const progress = getProgress();
  const isChildrenApplicable =
    state && !(state.has_children.status === 'confirmed' && state.has_children.value === false);

  if (currentPath !== '/chat' && currentPath !== '/edit') {
    return (
      <div key="landing" className="landing-page fade-in">
        <header className="landing-header">
          <div className="landing-logo">
            <span className="landing-logo-text">Wenup AI</span>
          </div>
          <div className="landing-profile">
            <img src={personImg} alt="Profile" className="profile-pic" />
          </div>
        </header>
        <h1 className="landing-title">
          Document Intake<br />Assistant
        </h1>
        <button className="btn-start" onClick={() => navigate('/chat')}>
          Start Conversation
        </button>
        <p className="landing-description">
          Seamlessly record your personal wishes through a natural, guided conversation. Our intelligent assistant will collect your details and instantly generate a beautifully formatted, ready-to-print PDF document for your loved ones.
        </p>
      </div>
    );
  }

  return (
    <div key="chat" className="fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header className="app-header">
        <div className="landing-logo">
          <span className="landing-logo-text">Wenup AI</span>
        </div>
        <div className="header-actions">
          <button className="btn-reset" onClick={handleReset} id="btn-reset" title="Start Over" style={{ padding: '0', background: 'transparent', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <img src={startImg} alt="Start Over" style={{ width: '32px', height: '32px', cursor: 'pointer' }} />
          </button>
          <img src={personImg} alt="Profile" className="profile-pic" style={{ marginLeft: '12px' }} />
        </div>
      </header>

      {/* Main Layout wrapper for scrollbar far right */}
      <div className="app-main-wrapper">
        <main className="app-main">
          {/* Group 1: Chat + Preview */}
          {currentPath === '/chat' && (
            <div className="layout-group">
            {/* Chat Panel */}
            <div className="panel chat-group-panel">
              <div className="panel-header">
                <div className="panel-title">
                  <img src={chatImg} alt="Chat Icon" className="panel-title-icon-img" /> Chat
                </div>
              </div>
              <div className="panel-body" ref={chatScrollRef}>
                <div className="chat-messages">
                  {messages.map((m, i) => (
                    <div key={i} className={`message message-${m.role}`}>
                      {m.role === 'assistant' && (
                        <div className="message-avatar avatar-assistant">
                          <img src={asstentImg} alt="Assistant" />
                        </div>
                      )}
                      <div className="message-bubble">{m.content}</div>
                      {m.role === 'user' && (
                        <div className="message-avatar avatar-user">
                          <img src={personImg} alt="User" />
                        </div>
                      )}
                    </div>
                  ))}
                  {isSending && (
                    <div className="typing-indicator">
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                    </div>
                  )}
                </div>
              </div>
              <div className="chat-input-area">
                <div className="chat-input-wrapper">
                  <textarea
                    ref={inputRef}
                    className="chat-input"
                    placeholder="Type your message… (Enter to send, Shift+Enter for new line)"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isSending}
                    rows={1}
                    id="chat-input"
                  />
                  <button
                    className="btn-send"
                    onClick={handleSend}
                    disabled={isSending || !inputText.trim()}
                    id="btn-send"
                  >
                    ➤
                  </button>
                </div>
              </div>
            </div>

            {/* Document Panel 1 (Next to Chat) */}
            <div className="panel chat-group-panel">
              <div className="panel-header">
                <div className="panel-title">
                  <img src={previewImg} alt="Preview Icon" className="panel-title-icon-img" /> Live Preview
                </div>
                <div className="doc-actions">
                  <button className="btn-doc-action" onClick={() => setCurrentPath('/edit')} id="btn-edit-doc-1">
                    <img src={editImg} alt="Edit Icon" className="btn-action-icon" /> Edit
                  </button>
                  <button className="btn-doc-action" onClick={handleDownloadDoc} id="btn-download-doc-1">
                    <img src={downloadImg} alt="Download Icon" className="btn-action-icon" style={{ filter: 'brightness(0)' }} /> Download
                  </button>
                </div>
              </div>
              <div className="panel-body">
                <div className="document-content">
                  {state ? <DocumentTemplate state={state} /> : <div style={{ padding: '2rem' }}>Loading template...</div>}
                </div>
              </div>
            </div>
            </div>
          )}

          {/* Group 2: Edit + Preview */}
          {currentPath === '/edit' && (
            <>
            <div className="layout-group">
            {/* State Panel */}
            <div className="panel" style={{ backgroundColor: 'transparent', boxShadow: 'none', border: 'none', overflowY: 'visible', padding: 0 }}>
              <EditPanel state={state} onSave={handleBatchEdit} />
            </div>

            {/* Document Panel 2 (Next to Edit) */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">
                  <img src={previewImg} alt="Preview Icon" className="panel-title-icon-img" /> Live Preview
                </div>
                <div className="doc-actions">
                  <button className="btn-doc-action" onClick={() => setCurrentPath('/chat')} id="btn-edit-doc-2">
                    <img src={chatImg} alt="Chat Icon" className="btn-action-icon" style={{ filter: 'brightness(0)' }} /> Back to Chat
                  </button>
                  <button className="btn-doc-action" onClick={handleDownloadDoc} id="btn-download-doc-2">
                    <img src={downloadImg} alt="Download Icon" className="btn-action-icon" style={{ filter: 'brightness(0)' }} /> Download
                  </button>
                </div>
              </div>
              <div className="panel-body">
                <div className="document-content">
                  {state ? <DocumentTemplate state={state} /> : <div style={{ padding: '2rem' }}>Loading template...</div>}
                </div>
              </div>
            </div>
          </div>
          
          {/* Download Button Centered Below Group 2 */}
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '1rem' }}>
            <button className="btn-massive-download" onClick={handleDownloadDoc} style={{ width: '50%', maxWidth: '600px' }}>
              <img src={downloadImg} alt="Download Icon" className="btn-massive-download-icon" /> Download PDF Document
            </button>
          </div>
          </>
          )}
        </main>
      </div>

      {/* Mobile tabs */}
      <div className="mobile-tabs">
        <button
          className={`mobile-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat
        </button>
        <button
          className={`mobile-tab ${activeTab === 'state' ? 'active' : ''}`}
          onClick={() => setActiveTab('state')}
        >
          📊 Fields
        </button>
        <button
          className={`mobile-tab ${activeTab === 'document' ? 'active' : ''}`}
          onClick={() => setActiveTab('document')}
        >
          📄 Document
        </button>
      </div>

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="notification-area">
          {notifications.map((n) => (
            <div key={n.id} className={`notification notification-${n.type}`}>
              <span>{n.type === 'error' ? '⚠' : 'ℹ'}</span>
              <span>{n.text}</span>
              <button
                className="notification-dismiss"
                onClick={() => dismissNotification(n.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
