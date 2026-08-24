import React, { useState, useRef, useEffect } from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { copilotAPI } from '../../services/api';
import { MessageSquare, Send, X, Bot, User, Maximize2, Minimize2, Loader } from 'lucide-react';

export default function CopilotPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI Copilot. How can I assist you with this investigation today?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [lastClaimId, setLastClaimId] = useState(null);
  const messagesEndRef = useRef(null);

  const {
    activeClaimId,
    activeInvestigationId,
    claimData,
    investigationData,
    traceData,
    findingsData
  } = useInvestigation();

  // Reset conversation when claim changes
  useEffect(() => {
    if (activeClaimId && activeClaimId !== lastClaimId) {
      setMessages([
        { role: 'assistant', content: `Hello! I am now assisting you with investigation for claim ${activeClaimId}. How can I help?` }
      ]);
      setConversationId(null); // Reset conversation ID to start fresh
      setLastClaimId(activeClaimId);
    }
  }, [activeClaimId, lastClaimId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // Use investigation_id if available, otherwise use claim_id
      const queryId = activeInvestigationId || activeClaimId;
      
      if (!queryId) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'No active claim or investigation found. Please select a claim first.'
        }]);
        setIsTyping(false);
        return;
      }

      const payload = {
        investigation_id: queryId,  // Can be investigation_id OR claim_id
        question: userMsg.content,
        conversation_id: conversationId
      };

      const response = await copilotAPI.query(payload);
      
      // Store conversation_id from response for continuity
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      const formatResponse = (resp) => {
        if (typeof resp === 'string') return resp;
        let md = '';
        if (resp.answer) md += resp.answer;
        if (resp.explanation) md += `\n\n${resp.explanation}`;
        if (resp.caveat) md += `\n\n⚠️ ${resp.caveat}`;
        if (resp.evidence && resp.evidence.length > 0) {
          md += '\n\nEvidence:\n' + resp.evidence.map(e => `• ${e.summary || e.id}`).join('\n');
        }
        return md || JSON.stringify(resp, null, 2);
      };

      setMessages(prev => [...prev, { role: 'assistant', content: formatResponse(response) }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I am temporarily unavailable. Please try again later.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 p-4 bg-rose-600 text-white rounded-full shadow-xl hover:bg-rose-700 transition-all z-50 flex items-center justify-center group"
      >
        <MessageSquare size={24} />
        <span className="max-w-0 overflow-hidden whitespace-nowrap group-hover:max-w-xs transition-all duration-300 ease-in-out pl-0 group-hover:pl-2 font-semibold">
          AI Copilot
        </span>
      </button>
    );
  }

  return (
    <div className={`fixed bottom-0 right-6 bg-white shadow-2xl border border-slate-200 rounded-t-xl z-50 flex flex-col transition-all duration-300 ${isExpanded ? 'w-[600px] h-[80vh]' : 'w-[380px] h-[550px]'}`}>
      {/* Header */}
      <div className="bg-slate-900 text-white p-4 rounded-t-xl flex justify-between items-center cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        <div>
          <div className="flex items-center gap-2">
            <Bot size={20} className="text-rose-400" />
            <h3 className="font-bold">ClaimGuard Copilot</h3>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-300">
             <span>Case: {activeClaimId}</span>
             <span className="w-1 h-1 bg-slate-500 rounded-full"></span>
             <span className="flex items-center gap-1">
                {investigationData?.status === 'COMPLETED' ? (
                   <><span className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span> Investigation Completed</>
                ) : (
                   <><span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></span> Investigation Active</>
                )}
             </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="text-slate-400 hover:text-white" onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}>
            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button className="text-slate-400 hover:text-white" onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}>
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-slate-200' : 'bg-rose-100 text-rose-600'}`}>
                {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className={`p-3 rounded-2xl text-sm whitespace-pre-wrap ${msg.role === 'user' ? 'bg-slate-800 text-white rounded-tr-none' : 'bg-white border border-slate-200 text-slate-700 rounded-tl-none shadow-sm'}`}>
                {msg.content}
              </div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="flex gap-3 max-w-[85%] flex-row">
              <div className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-rose-100 text-rose-600">
                <Bot size={14} />
              </div>
              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm rounded-tl-none flex items-center gap-2 text-slate-500">
                <Loader size={14} className="animate-spin" /> Thinking...
              </div>
            </div>
          </div>
        )}
        
        {/* Quick Actions (only show if not typing and at bottom) */}
        {!isTyping && messages.length < 3 && (
           <div className="flex flex-wrap gap-2 pt-2">
              <button onClick={() => setInput('Explain Risk')} className="text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm">Explain Risk</button>
              <button onClick={() => setInput('Summarize Evidence')} className="text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm">Summarize Evidence</button>
              <button onClick={() => setInput('Show Unresolved Questions')} className="text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm">Show Unresolved Questions</button>
              <button onClick={() => setInput('Summarize Investigation')} className="text-xs bg-white border border-slate-200 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-sm">Summarize Investigation</button>
           </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-slate-100">
        <form onSubmit={handleSend} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this investigation..."
            className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all"
            disabled={isTyping}
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-white bg-rose-600 rounded-lg hover:bg-rose-700 disabled:bg-slate-300 transition-colors"
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </div>
  );
}
