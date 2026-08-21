import { useState, useRef, useEffect } from 'react';
import { Bot, Send, User, Sparkles, RefreshCw } from 'lucide-react';
import PageHeader from '../../components/ui/PageHeader';

const presetQuestions = [
  'Summarize the Riverside Medical Center investigation',
  'What are the top fraud patterns detected this month?',
  'Explain the unbundling detected in CLM-2024-0075',
  'What documents are missing from INV-2024-0041?',
  'Suggest next steps for the cardiac bypass case',
];

const botResponses = {
  'Summarize the Riverside Medical Center investigation': `**Riverside Medical Center — Investigation Summary**\n\nRiverside Medical Center (PRV-001) currently has **2 active investigations** with a combined claim value of $139,950.\n\n**INV-2024-0041** (CLM-2024-0081) involves suspected duplicate billing for patient James Thornton. Conflicting admission dates were identified. Risk score: 82.\n\n**INV-2024-0039** (CLM-2024-0075) is a critical priority case involving suspected unbundling and upcoding on a cardiac bypass surgery claim for $91,750. CPT codes 33533, 33518, and 33530 were billed separately — these should be bundled under standard CCI edits, potentially reducing reimbursement by ~$34,000.\n\nOverall provider risk score: **72 (High)**. Recommend escalating INV-2024-0039 to senior review.`,
  'What are the top fraud patterns detected this month?': `**Top Fraud Patterns — July 2024**\n\n1. **Unbundling** (2 cases) — Procedures that should be billed together are being billed separately to inflate reimbursement. Estimated exposure: $180k.\n\n2. **Duplicate Billing** (1 case) — Same patient billed twice within 30 days for similar procedures.\n\n3. **Documentation Deficiency** (1 case) — Missing operative reports submitted with claims to obscure billing inconsistencies.\n\n4. **High-Cost Outliers** (2 cases) — Claims significantly above peer averages for the same procedure codes.\n\nTotal estimated savings if resolved: **$384,000**.`,
  'Explain the unbundling detected in CLM-2024-0075': `**Unbundling Analysis — CLM-2024-0075**\n\nThis claim for patient Alan Brooks (cardiac bypass surgery, $91,750) shows classic unbundling:\n\n- **CPT 33533** (Arterial coronary artery bypass) — billed at full rate\n- **CPT 33518** (Additional arterial graft) — billed separately\n- **CPT 33530** (Reoperation add-on) — billed separately\n\nPer CCI (Correct Coding Initiative) edits, these codes should be bundled. Correct billing would use **33533 + 33518** together, removing the separate 33530 charge.\n\n**Impact:** ~$34,000 in overbilling. Recommended action: Deny the unbundled component and request provider resubmission with correct bundled codes.`,
  'What documents are missing from INV-2024-0041?': `**Missing Documents — INV-2024-0041**\n\nFor claim CLM-2024-0081 (James Thornton, Appendectomy, $48,200):\n\n✅ Claim Form UB-04 — Received\n✅ Medical Records — Received\n⚠️ **Operative Report** — Flagged (signature missing, procedure date inconsistency)\n\n**Recommended Actions:**\n1. Request corrected operative report from Riverside Medical Center\n2. Verify patient admission date against hospital system records\n3. Cross-reference with any prior claims for the same patient in the past 90 days`,
  'Suggest next steps for the cardiac bypass case': `**Recommended Next Steps — INV-2024-0039**\n\nThis is a **Critical Priority** case due July 17, 2024 (currently overdue).\n\n1. **Immediate:** Obtain the full operative report and cross-reference the CPT codes with the documented procedure.\n\n2. **Code Review:** Engage a certified coder to confirm whether the CCI bundling edit applies to the specific procedure combination.\n\n3. **Provider Contact:** Send a formal inquiry to Riverside Medical Center requesting clarification on why procedures were billed separately.\n\n4. **Peer Comparison:** Pull 5 comparable cardiac bypass claims from other providers for cost benchmarking.\n\n5. **Decision:** If unbundling is confirmed, issue a partial denial for the unbundled component and calculate the adjusted payment amount.`,
};

const defaultResponse = (q) =>
  `I've analyzed your query: **"${q}"**\n\nBased on the current investigation data, I can see relevant claim patterns and risk indicators. For detailed analysis, I recommend reviewing the Claims Repository and cross-referencing the provider's billing history.\n\nWould you like me to run a deeper analysis on a specific claim or provider?`;

const formatMessage = (text) => {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('**') && line.endsWith('**')) {
      return <p key={i} className="font-semibold text-slate-800 mb-1">{line.replace(/\*\*/g, '')}</p>;
    }
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={i} className="text-sm text-slate-700 leading-relaxed mb-1">
        {parts.map((part, j) =>
          part.startsWith('**') && part.endsWith('**')
            ? <strong key={j}>{part.replace(/\*\*/g, '')}</strong>
            : part
        )}
      </p>
    );
  });
};

export default function AICopilot() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      content: `Hello! I'm your **AI Case Copilot** for ClaimGuard. I can help you:\n\n- Summarize investigations and claims\n- Identify fraud patterns and anomalies\n- Suggest next steps for open cases\n- Explain detected billing irregularities\n\nHow can I assist you today?`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    const q = text.trim();
    if (!q) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    await new Promise(r => setTimeout(r, 900 + Math.random() * 600));
    const response = botResponses[q] || defaultResponse(q);
    setMessages(prev => [...prev, { role: 'bot', content: response }]);
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  return (
    <div className="flex flex-col h-full" style={{ height: 'calc(100vh - 120px)' }}>
      <PageHeader
        title="AI Case Copilot"
        subtitle="Ask questions about investigations, claims, and fraud patterns."
        actions={
          <button className="btn-secondary text-xs" onClick={() => setMessages([{
            role: 'bot',
            content: 'Conversation cleared. How can I help you?',
          }])}>
            <RefreshCw size={13} /> Clear Chat
          </button>
        }
      />

      <div className="flex gap-5 flex-1 min-h-0">
        {/* Presets */}
        <div className="hidden lg:block w-56 flex-shrink-0">
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={14} className="text-violet-500" />
              <p className="text-xs font-semibold text-slate-700">Quick Questions</p>
            </div>
            <div className="space-y-1.5">
              {presetQuestions.map(q => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="w-full text-left text-xs text-slate-600 px-2.5 py-2 rounded-lg hover:bg-violet-50 hover:text-violet-700 transition-colors leading-snug"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chat */}
        <div className="flex-1 flex flex-col min-w-0 card overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.role === 'bot' ? 'bg-violet-100 text-violet-700' : 'bg-rose-100 text-rose-700'
                }`}>
                  {msg.role === 'bot' ? <Bot size={14} /> : <User size={14} />}
                </div>
                <div className={`max-w-[75%] px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-rose-600 text-white rounded-tr-sm'
                    : 'bg-slate-50 border border-slate-100 rounded-tl-sm'
                }`}>
                  {msg.role === 'user'
                    ? <p className="text-sm text-white">{msg.content}</p>
                    : <div>{formatMessage(msg.content)}</div>
                  }
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-violet-100 text-violet-700 flex items-center justify-center flex-shrink-0">
                  <Bot size={14} />
                </div>
                <div className="px-4 py-3 bg-slate-50 border border-slate-100 rounded-2xl rounded-tl-sm">
                  <div className="flex gap-1 items-center h-4">
                    {[0, 1, 2].map(i => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-slate-100 p-4">
            <div className="flex items-end gap-2">
              <textarea
                className="flex-1 input resize-none min-h-[40px] max-h-28 py-2.5"
                placeholder="Ask about a case, claim, or fraud pattern…"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || loading}
                className="btn-primary flex-shrink-0 px-3 py-2.5 disabled:opacity-50"
              >
                <Send size={15} />
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1.5">Press Enter to send · Shift+Enter for new line</p>
          </div>
        </div>
      </div>
    </div>
  );
}
