import { useState, useRef, useEffect, useContext } from 'react';
import { Bot, Send, User, RefreshCw, Loader } from 'lucide-react';
import { copilotAPI } from '../../services/api';
import { InvestigationContext } from '../../context/InvestigationContext';
import PageHeader from '../../components/ui/PageHeader';

const QUICK_QUESTIONS = [
  'Why was this claim flagged?',
  'What ML factors contributed to the risk score?',
  'What evidence did the agent find?',
  'What policy supports this finding?',
  'What provider history was found?',
  'What are the unresolved evidence gaps?',
  'Summarize the investigation.',
];

export default function AICopilot() {
  const invCtx = useContext(InvestigationContext);
  const { activeInvestigationId, activeClaimId, investigationData } = invCtx || {};

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am your AI Case Copilot. I can answer questions about any active investigation.\n\nOpen a case from the Investigation Queue or navigate to a Case Detail page, then return here to ask questions about that investigation.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (question) => {
    const q = question || input.trim();
    if (!q) return;

    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setInput('');
    setLoading(true);

    try {
      if (!activeInvestigationId) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'No active investigation found. Please open a Case Detail page and start an investigation first, then return here to ask questions.',
        }]);
        return;
      }

      const response = await copilotAPI.query({
        investigation_id: activeInvestigationId,
        question: q,
      });

      let answer = '';
      if (typeof response === 'string') {
        answer = response;
      } else if (response?.answer) {
        answer = response.answer;
        if (response.explanation) answer += `\n\n${response.explanation}`;
        if (response.caveat) answer += `\n\n⚠️ Note: ${response.caveat}`;
        if (response.evidence?.length > 0) {
          answer += '\n\nEvidence:\n' + response.evidence.map(e => `• ${e.summary || e.id}`).join('\n');
        }
        if (response.citations?.length > 0) {
          answer += '\n\nCitations:\n' + response.citations.map(c => `• ${c.title || c.source}`).join('\n');
        }
      } else {
        answer = JSON.stringify(response, null, 2);
      }

      setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message || 'Copilot temporarily unavailable.'}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleSend();
  };

  const clearHistory = () => {
    setMessages([{
      role: 'assistant',
      content: activeInvestigationId
        ? `Conversation cleared. I'm still focused on investigation ${activeInvestigationId} for claim ${activeClaimId}. Ask me anything.`
        : 'Conversation cleared. No active investigation. Open a case to begin.',
    }]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-w-4xl mx-auto">
      <PageHeader
        title="AI Investigator Copilot"
        subtitle={activeInvestigationId
          ? `Active: Case ${activeClaimId} · Investigation ${activeInvestigationId}`
          : 'Open a case to enable investigation-grounded answers'}
        actions={
          <button
            onClick={clearHistory}
            className="text-xs flex items-center gap-1 text-slate-500 hover:text-slate-800 transition"
          >
            <RefreshCw size={13} /> Clear History
          </button>
        }
      />

      {/* Context Banner */}
      {activeInvestigationId && (
        <div className="mx-0 mb-4 px-4 py-2 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700 flex items-center gap-2">
          <Bot size={14} className="shrink-0" />
          Copilot is grounded in investigation <strong>{activeInvestigationId}</strong> for claim <strong>{activeClaimId}</strong>
          {investigationData?.status && <span className="ml-auto font-bold">{investigationData.status}</span>}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 px-1 py-2">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-slate-200' : 'bg-rose-100 text-rose-600'}`}>
                {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className={`p-4 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed ${msg.role === 'user'
                ? 'bg-slate-800 text-white rounded-tr-none'
                : 'bg-white border border-slate-200 text-slate-700 rounded-tl-none shadow-sm'}`}>
                {msg.content}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="flex gap-3 max-w-[85%]">
              <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-rose-100 text-rose-600">
                <Bot size={14} />
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm rounded-tl-none flex items-center gap-2 text-slate-500">
                <Loader size={14} className="animate-spin" /> Thinking...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Questions */}
      {!loading && messages.length < 4 && activeInvestigationId && (
        <div className="flex flex-wrap gap-2 py-3 border-t border-slate-100">
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              className="text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-50 hover:border-slate-300 transition shadow-sm"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="pt-3 border-t border-slate-100 bg-white">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={activeInvestigationId ? 'Ask about this investigation...' : 'Open a case first to ask investigation-specific questions...'}
            className="w-full pl-4 pr-14 py-3.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 text-white bg-rose-600 rounded-lg hover:bg-rose-700 disabled:bg-slate-300 transition-colors"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
