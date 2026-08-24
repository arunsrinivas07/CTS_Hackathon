import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { Bot, X, Send, Sparkles, MessageCircle, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import { claimsAPI, investigationsAPI } from '../../services/api';

// Context resolver based on current path
function resolveContext(pathname) {
  // 1. Investigation Workspace Context
  if (pathname.includes('/investigations/') || pathname.includes('/investigator/case/')) {
    const parts = pathname.split('/');
    const id = parts[parts.length - 1];
    return {
      type: 'CLAIM',
      title: `Claim Assistant · ${id || 'Active Claim'}`,
      badge: `CLAIM · ${id || 'Active'}`,
      id: id,
      entity: null
    };
  }

  // 2. Document Verification Context
  if (pathname.includes('/investigator/documents')) {
    const parts = pathname.split('/');
    const claimId = parts[parts.length - 1] !== 'documents' ? parts[parts.length - 1] : null;
    return {
      type: 'DOCUMENT',
      title: claimId ? `Evidence Assistant · ${claimId}` : 'Evidence Assistant',
      badge: claimId ? `DOCUMENT · ${claimId}` : 'DOCUMENT',
      id: claimId,
      entity: null
    };
  }

  // 3. Provider Intelligence Context
  if (pathname.includes('/investigator/providers')) {
    return {
      type: 'PROVIDER',
      title: 'Provider Assistant · Provider Intelligence',
      badge: 'PROVIDER · AUDIT',
      id: 'PRV-001',
      entity: null
    };
  }

  // 4. Investigation Reports Context
  if (pathname.includes('/investigator/reports')) {
    return {
      type: 'REPORT',
      title: 'Reports Assistant',
      badge: 'REPORT · ARCHIVE',
      id: 'REP-ARCHIVE',
      entity: null
    };
  }

  // Default Global Mode
  return {
    type: 'GLOBAL',
    title: 'Investigator Assistant',
    badge: 'GLOBAL',
    id: null,
    entity: null
  };
}

export default function FloatingAIChat() {
  const { pathname } = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      content: "Hello! I am your clinical audit assistant. I can help resolve queries based on claim history, provider files, and guideline benchmarks."
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const context = resolveContext(pathname);

  // Dynamic suggested questions based on context
  const getSuggestions = () => {
    switch (context.type) {
      case 'CLAIM':
        return [
          'Why was this claim reviewed?',
          'What evidence is still missing?',
          'Summarize the strongest concerns.'
        ];
      case 'PROVIDER':
        return [
          'Why is this provider high risk?',
          'Show unusual billing patterns',
          'Compare with regional peers'
        ];
      case 'DOCUMENT':
        return [
          'Why was the operative report flagged?',
          'Explain the verification result'
        ];
      case 'REPORT':
        return [
          'Summarize previous audit reports',
          'What are the strongest findings?'
        ];
      default:
        return [
          'Show critical investigations',
          'Explain risk levels',
          'Find unusual providers'
        ];
    }
  };

  // Conversational response mock logic (jargon-free)
  const getGroundedResponse = (q) => {
    const qLower = q.toLowerCase();

    if (context.type === 'CLAIM') {
      const claimId = context.id;
      const claimData = context.entity?.cl;
      const invData = context.entity?.inv;

      if (qLower.includes('why') || qLower.includes('reviewed') || qLower.includes('flagged') || qLower.includes('concern')) {
        return `Review of claim **${claimId}** is driven by a procedure charge of **$4,000** for Urine Drug Screen (CPT 80307), representing a **11.1x fee schedule variance** above the regional average ($380). Clinical timelines also conflict with facility admission logs.`;
      }
      if (qLower.includes('evidence') || qLower.includes('missing') || qLower.includes('request')) {
        return `Outstanding evidence requirements for **${claimId}** include:
1. **Detailed Physician Progress Notes** (High Priority) - to substantiate procedure complexity.
2. **Laboratory / Diagnostic Reports** (High Priority) - to validate medical necessity.
3. **Pre-Authorization Documentation** (Medium Priority).`;
      }
      if (qLower.includes('compare') || qLower.includes('peer') || qLower.includes('similar')) {
        return `Comparable regional claims for CPT 80307 fall within a standard range of **$350–$420**. The billed amount of **$4,000** sits significantly outside observed billing patterns.`;
      }
      return `For claim **${claimId}**, the direct financial exposure is **$${claimData?.amount?.toLocaleString() || 'N/A'}** for patient **${claimData?.patient || 'N/A'}**. I can provide details on missing evidence, risk indicators, or next steps.`;
    }

    if (context.type === 'PROVIDER') {
      if (qLower.includes('why') || qLower.includes('risk')) {
        return `Provider risk profiles are evaluated based on billing frequency percentiles, fee schedule variances, and ML anomaly scores.`;
      }
      if (qLower.includes('pattern') || qLower.includes('unusual')) {
        return `Unusual billing patterns include high-volume billing clusters within narrow time windows exceeding peer benchmark thresholds.`;
      }
      if (qLower.includes('compare') || qLower.includes('peer')) {
        return `**Peer Comparison:**
- Billed CPT code average vs. CMS regional benchmarks
- Feature vector variance ratios evaluated via Hybrid XGBoost/IsolationForest model.`;
      }
      return `For provider analysis, high-risk provider accounts are prioritized for clinical audit and recovery evaluation.`;
    }

    if (context.type === 'DOCUMENT') {
      if (qLower.includes('why') || qLower.includes('flagged') || qLower.includes('operative')) {
        return `Document flags occur when physician signature logs are missing or service dates conflict with admission records.`;
      }
      if (qLower.includes('verification') || qLower.includes('ocr') || qLower.includes('result')) {
        return `Text scanning and digital stamps have been validated. Document details can be cross-referenced against line items.`;
      }
      return `Document Verification checks digital credentials and procedure codes against operative notes.`;
    }

    if (context.type === 'REPORT') {
      if (qLower.includes('summarize') || qLower.includes('previous') || qLower.includes('audit')) {
        return `Audit Report Summary:
- **Status:** Evaluated via live REST API
- **Key Finding:** Pre-payment hold requested on anomalous CPT billing codes.`;
      }
      return `You are viewing the Investigation Reports index. Select a claim link to route to the workspace or download report details.`;
    }

    // Global Mode Answers
    if (qLower.includes('critical') || qLower.includes('priority')) {
      return `Critical priority cases in the active queue present high anomaly scores or LEIE gatekeeper exclusions.`;
    }
    if (qLower.includes('workflow') || qLower.includes('risk')) {
      return `Claims with outlier costs, date timeline conflicts, or documentation deficiencies route to the queue for clinical review. Claims are resolved once required evidence is verified or repriced.`;
    }

    return `I've analyzed your query: **"${q}"** in Global Mode. I can locate high-risk providers, summarize critical cases, and explain risk drivers. Ask any question about active claims or provider intelligence.`;
  };

  const handleSend = async (text) => {
    const q = text.trim();
    if (!q) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);

    // Simulate response delay
    await new Promise(r => setTimeout(r, 600));

    const response = getGroundedResponse(q);
    setMessages(prev => [...prev, { role: 'bot', content: response }]);
    setLoading(false);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset chat context messages when context changes
  useEffect(() => {
    setMessages([
      {
        role: 'bot',
        content: `Hello! I have updated my context to **${context.title}**. Ask me any specific audit queries.`
      }
    ]);
  }, [context.title]);

  const formatMessage = (text) => {
    return text.split('\n').map((line, i) => {
      const parts = line.split(/(\*\*[^*]+\*\*)/g);
      return (
        <p key={i} className="text-xs text-slate-700 leading-relaxed mb-1">
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**')
              ? <strong key={j} className="font-bold text-slate-900">{part.replace(/\*\*/g, '')}</strong>
              : part
          )}
        </p>
      );
    });
  };

  return (
    <>
      {/* ─── FLOATING TOGGLE BUTTON ─── */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full flex items-center justify-center text-white shadow-2xl transition-all duration-300 z-50 cursor-pointer bg-[#9f1239] hover:bg-[#7c2d3e] hover:scale-105"
        style={{ boxShadow: '0 8px 30px rgba(159,18,57,0.4)' }}
      >
        {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
      </button>

      {/* ─── SLIDE PANEL ─── */}
      {isOpen && (
        <div
          className="fixed inset-y-0 right-0 w-full sm:w-[420px] bg-white border-l shadow-2xl z-50 flex flex-col animate-slide-in"
          style={{ height: '100vh', borderColor: '#E7E1DC' }}
        >
          {/* Header */}
          <div className="p-4 border-b bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-rose-600 animate-pulse" />
              <div>
                <h3 className="text-sm font-bold text-slate-800">{context.title}</h3>
                {/* Context Badge */}
                <span className="inline-flex items-center gap-1 text-[9px] font-extrabold uppercase bg-rose-100 text-rose-800 px-2.5 py-0.5 rounded-full border border-rose-200">
                  <Sparkles size={8} />
                  {context.badge}
                </span>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 items-start ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${msg.role === 'bot' ? 'bg-rose-100 text-rose-700' : 'bg-slate-200 text-slate-700'
                  }`}>
                  {msg.role === 'bot' ? 'AI' : 'ME'}
                </div>
                <div className={`p-3 rounded-2xl max-w-[80%] border ${msg.role === 'user'
                  ? 'bg-[#9f1239] text-white rounded-tr-none border-[#9f1239] text-xs'
                  : 'bg-slate-50 text-slate-800 rounded-tl-none border-slate-100'
                  }`}>
                  {msg.role === 'user'
                    ? <p className="text-xs text-white">{msg.content}</p>
                    : <div>{formatMessage(msg.content)}</div>
                  }
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-2.5 items-start">
                <div className="w-6 h-6 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[10px] font-bold">
                  AI
                </div>
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-2xl rounded-tl-none flex items-center gap-1">
                  <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                  <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                  <div className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggested Questions */}
          <div className="p-3 border-t bg-slate-50 space-y-1.5">
            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider block">Suggested Questions</span>
            <div className="flex flex-wrap gap-1.5">
              {getSuggestions().map(q => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-[10px] text-left bg-white border border-slate-200 rounded-lg py-1 px-2 hover:bg-rose-50 hover:text-rose-700 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Form Input */}
          <div className="p-3 border-t flex gap-2 items-center">
            <input
              className="flex-1 input text-xs py-2 bg-slate-50 border-slate-200"
              placeholder="Ask anything about current audit context..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSend(input); }}
            />
            <button
              onClick={() => handleSend(input)}
              disabled={!input.trim() || loading}
              className="btn-primary text-xs p-2 bg-[#9f1239] hover:bg-[#7c2d3e] disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
