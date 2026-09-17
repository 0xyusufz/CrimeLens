"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiClient } from "../lib/apiClient";

function TabIcon({ name }) {
  if (name === "matrix") {
    return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>;
  }
  if (name === "brief") {
    return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h6" /></svg>;
  }
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" /><path d="M8 11h.01M12 11h.01M16 11h.01" strokeWidth="2.5" strokeLinecap="round" /></svg>;
}

function RefreshIcon() {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M21 12a9 9 0 0 1-15.4 6.3L3 16M3 12A9 9 0 0 1 18.4 5.7L21 8" /><path d="M3 21v-5h5M21 3v5h-5" /></svg>;
}

export default function CaseCopilotView({ caseId }) {
  const [networkTables, setNetworkTables] = useState(null);
  const [loadingTables, setLoadingTables] = useState(true);
  const [brief, setBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "I can help you review verified case connections, extracted entities, and evidence context. Ask about a person, relationship, financial trail, or document finding.",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState("chat");
  const chatEndRef = useRef(null);

  // Existing API contracts deliberately remain unchanged.
  const fetchTables = useCallback(async () => {
    if (!caseId) return;
    setLoadingTables(true);
    try {
      const data = await apiClient(`/api/cases/${caseId}/intelligence/tables`);
      setNetworkTables(data);
    } catch (err) {
      console.error("Failed to load network tables:", err);
    } finally {
      setLoadingTables(false);
    }
  }, [caseId]);

  const generateBrief = useCallback(async () => {
    if (!caseId) return;
    setLoadingBrief(true);
    try {
      const data = await apiClient(`/api/cases/${caseId}/intelligence/brief`);
      setBrief(data.brief);
    } catch (err) {
      console.error("Failed to generate brief:", err);
      setBrief("Unable to generate a network brief at this time.");
    } finally {
      setLoadingBrief(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || isQuerying) return;

    const userText = inputQuery.trim();
    setInputQuery("");
    const newHistory = [...messages, { role: "user", content: userText }];
    setMessages(newHistory);
    setIsQuerying(true);

    try {
      const response = await apiClient(`/api/cases/${caseId}/intelligence/copilot`, {
        method: "POST",
        body: JSON.stringify({
          question: userText,
          history: newHistory.map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: response.answer || "No response received." }]);
    } catch (err) {
      console.error("Copilot query failed:", err);
      setMessages((prev) => [...prev, { role: "assistant", content: "The case intelligence service could not complete that request. Please verify connectivity and try again." }]);
    } finally {
      setIsQuerying(false);
    }
  };

  const selectTab = (tab) => {
    setActiveSubTab(tab);
    if (tab === "brief" && !brief && !loadingBrief) generateBrief();
  };

  return (
    <div className="copilot-root">
      <header className="copilot-header">
        <div className="copilot-heading">
          <div className="copilot-heading-mark" aria-hidden="true"><TabIcon name="chat" /></div>
          <div>
            <span className="copilot-eyebrow"><span className="copilot-live-dot" /> CASE INTELLIGENCE</span>
            <h3>Investigator Copilot</h3>
            <p>Grounded responses from the case network and registered evidence.</p>
          </div>
        </div>

        <nav className="copilot-tabs" aria-label="Copilot workspace views">
          <button className={activeSubTab === "chat" ? "copilot-tab is-active" : "copilot-tab"} onClick={() => selectTab("chat")}>
            <TabIcon name="chat" /> <span>Ask Copilot</span>
          </button>
          <button className={activeSubTab === "table" ? "copilot-tab is-active" : "copilot-tab"} onClick={() => selectTab("table")}>
            <TabIcon name="matrix" /> <span>Relations</span><b>{networkTables?.relationships_count ?? 0}</b>
          </button>
          <button className={activeSubTab === "brief" ? "copilot-tab is-active" : "copilot-tab"} onClick={() => selectTab("brief")}>
            <TabIcon name="brief" /> <span>Brief</span>
          </button>
        </nav>
      </header>

      {activeSubTab === "chat" && (
        <section className="copilot-chat-panel" aria-label="Case intelligence conversation">
          <div className="copilot-chat-topline">
            <span>Verified case context</span>
            <span>Responses require investigator review</span>
          </div>
          <div className="copilot-messages">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              return (
                <article className={isUser ? "copilot-message is-user" : "copilot-message"} key={`${message.role}-${index}`}>
                  <span className="copilot-message-author">{isUser ? "INVESTIGATOR" : "CRIMELENS COPILOT"}</span>
                  <p>{message.content}</p>
                </article>
              );
            })}
            {isQuerying && (
              <div className="copilot-thinking" aria-live="polite"><span /><span /><span /> Reviewing the case network…</div>
            )}
            <div ref={chatEndRef} />
          </div>
          <form onSubmit={handleSendMessage} className="copilot-composer">
            <label className="sr-only" htmlFor="copilot-query">Ask the investigator copilot</label>
            <input
              id="copilot-query"
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask about a person, account, relationship, or source document…"
              disabled={isQuerying}
            />
            <button type="submit" disabled={isQuerying || !inputQuery.trim()}>
              <span>Send inquiry</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></svg>
            </button>
          </form>
        </section>
      )}

      {activeSubTab === "table" && (
        <section className="copilot-data-panel">
          <div className="copilot-panel-heading">
            <div>
              <span className="copilot-eyebrow">NETWORK REGISTER</span>
              <h4>Relations matrix</h4>
              <p>A read-only view of extracted connections and their cited case context.</p>
            </div>
            <button className="copilot-secondary-action" onClick={fetchTables} disabled={loadingTables}><RefreshIcon /> Refresh</button>
          </div>
          {loadingTables ? (
            <div className="copilot-empty-state"><i className="copilot-spinner" /> Loading the relations register…</div>
          ) : (
            <div className="copilot-registers">
              <article className="copilot-register">
                <h5>Relationships</h5>
                <pre>{networkTables?.relationships_table_md || "No relationships are available for this case."}</pre>
              </article>
              <article className="copilot-register">
                <h5>Entity inventory</h5>
                <pre>{networkTables?.entities_table_md || "No entities are available for this case."}</pre>
              </article>
            </div>
          )}
        </section>
      )}

      {activeSubTab === "brief" && (
        <section className="copilot-data-panel copilot-brief-panel">
          <div className="copilot-panel-heading">
            <div>
              <span className="copilot-eyebrow">INVESTIGATIVE SUMMARY</span>
              <h4>Network intelligence brief</h4>
              <p>A concise synthesis of the available relationship graph and evidence context.</p>
            </div>
            <button className="copilot-primary-action" onClick={generateBrief} disabled={loadingBrief}><RefreshIcon /> {loadingBrief ? "Preparing brief" : "Refresh brief"}</button>
          </div>
          {loadingBrief ? (
            <div className="copilot-empty-state"><i className="copilot-spinner" /> Preparing an evidence-aware summary…</div>
          ) : (
            <article className="copilot-brief-content">{brief || "Select “Refresh brief” to generate an investigator-ready network summary."}</article>
          )}
        </section>
      )}

      <style jsx>{`
        .copilot-root { display:flex; flex-direction:column; min-height:620px; background:#fff; color:#1e3048; }
        .copilot-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1.2rem 1.35rem; border-bottom:1px solid #e0eaf2; background:linear-gradient(110deg,#fff 0%,#f4fbff 100%); }
        .copilot-heading { display:flex; align-items:center; gap:.85rem; min-width:0; }.copilot-heading-mark { width:38px; height:38px; display:grid; place-items:center; color:#087ec2; background:#e5f5ff; border:1px solid #c0e7fb; border-radius:10px; }.copilot-heading-mark :global(svg) { width:19px; height:19px; }
        .copilot-eyebrow { display:flex; align-items:center; gap:.38rem; color:#71839b; font-size:.64rem; font-weight:800; letter-spacing:.075em; }.copilot-live-dot { width:6px; height:6px; border-radius:50%; background:#0aae7a; box-shadow:0 0 0 3px rgba(12,170,120,.12); }.copilot-heading h3, .copilot-panel-heading h4 { margin:.12rem 0 .2rem; color:#1c2d44; font-size:1rem; letter-spacing:-.015em; }.copilot-heading p, .copilot-panel-heading p { margin:0; color:#73859b; font-size:.76rem; line-height:1.45; }
        .copilot-tabs { display:flex; align-items:center; gap:.35rem; padding:.28rem; background:#fff; border:1px solid #dce7f1; border-radius:10px; }.copilot-tab { display:inline-flex; align-items:center; gap:.38rem; padding:.48rem .62rem; color:#64778f; background:transparent; border:1px solid transparent; border-radius:7px; font-size:.74rem; font-weight:650; transition:.16s ease; }.copilot-tab :global(svg) { width:15px; height:15px; }.copilot-tab b { min-width:16px; padding:0 .26rem; border-radius:9px; color:#6c7e94; background:#edf3f7; font-size:.62rem; line-height:1.35rem; }.copilot-tab:hover { color:#087ec2; background:#f4fbff; }.copilot-tab.is-active { color:#087ec2; background:#e7f5ff; border-color:#c2e9fb; }.copilot-tab.is-active b { color:#087ec2; background:#d4effc; }
        .copilot-chat-panel { display:flex; flex:1; flex-direction:column; min-height:540px; }.copilot-chat-topline { display:flex; justify-content:space-between; padding:.55rem 1.35rem; color:#8091a5; background:#fbfdff; border-bottom:1px solid #e7eef4; font-size:.68rem; font-weight:600; }.copilot-messages { display:flex; flex:1; flex-direction:column; gap:.85rem; min-height:400px; max-height:520px; overflow-y:auto; padding:1.3rem; background:radial-gradient(circle at 5% 0,rgba(78,183,236,.08),transparent 18rem),#fff; }
        .copilot-message { align-self:flex-start; max-width:min(80%,680px); padding:.8rem .9rem; background:#f7fbfe; border:1px solid #dce8f1; border-radius:4px 12px 12px 12px; box-shadow:0 4px 12px rgba(38,75,105,.035); }.copilot-message.is-user { align-self:flex-end; background:#087ec2; border-color:#087ec2; border-radius:12px 4px 12px 12px; box-shadow:0 6px 15px rgba(7,126,194,.15); }.copilot-message-author { display:block; margin-bottom:.35rem; color:#087ec2; font-size:.61rem; font-weight:800; letter-spacing:.075em; }.is-user .copilot-message-author { color:#d7f2ff; }.copilot-message p { margin:0; color:#475d74; font-size:.84rem; line-height:1.6; white-space:pre-wrap; }.is-user p { color:#fff; }
        .copilot-thinking { display:flex; align-items:center; align-self:flex-start; gap:.3rem; padding:.65rem .8rem; color:#7690a6; background:#f8fbfd; border:1px solid #e0eaf2; border-radius:8px; font-size:.75rem; }.copilot-thinking span { width:5px; height:5px; background:#0a93db; border-radius:50%; animation:dotPulse 1s infinite alternate; }.copilot-thinking span:nth-child(2) { animation-delay:.2s; }.copilot-thinking span:nth-child(3) { animation-delay:.4s; } @keyframes dotPulse { to { opacity:.3; transform:translateY(-2px); } }
        .copilot-composer { display:flex; gap:.6rem; padding:.9rem 1.1rem; background:#fff; border-top:1px solid #e0eaf2; }.copilot-composer input { flex:1; min-width:0; height:42px; padding:0 .85rem; color:#26384f; background:#fbfdff; border:1px solid #d7e3ed; border-radius:8px; font-size:.82rem; }.copilot-composer input::placeholder { color:#9aaaba; }.copilot-composer input:focus { outline:0; border-color:#0787d1; box-shadow:0 0 0 3px rgba(7,135,209,.11); }.copilot-composer button, .copilot-primary-action, .copilot-secondary-action { display:inline-flex; align-items:center; justify-content:center; gap:.42rem; height:42px; padding:0 .85rem; border-radius:8px; font-size:.76rem; font-weight:700; transition:.16s ease; }.copilot-composer button, .copilot-primary-action { color:#fff; background:#0787d1; border:1px solid #0787d1; }.copilot-composer button:hover:not(:disabled), .copilot-primary-action:hover:not(:disabled) { background:#056eaf; }.copilot-composer button:disabled, .copilot-primary-action:disabled, .copilot-secondary-action:disabled { opacity:.55; cursor:not-allowed; }.copilot-composer :global(svg), .copilot-primary-action :global(svg), .copilot-secondary-action :global(svg) { width:15px; height:15px; }
        .copilot-data-panel { flex:1; padding:1.45rem; background:#fff; }.copilot-panel-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; padding-bottom:1.2rem; border-bottom:1px solid #e0eaf2; }.copilot-panel-heading h4 { font-size:1.05rem; }.copilot-secondary-action { color:#52677e; background:#fff; border:1px solid #d7e2ec; }.copilot-secondary-action:hover:not(:disabled) { color:#087ec2; border-color:#aadcf2; background:#f4fbff; }.copilot-registers { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1.2rem; }.copilot-register { overflow:hidden; border:1px solid #dce7f1; border-radius:10px; }.copilot-register h5 { margin:0; padding:.72rem .85rem; color:#40536b; background:#f6fbfe; border-bottom:1px solid #e0eaf2; font-size:.73rem; font-weight:750; letter-spacing:.02em; }.copilot-register pre { min-height:250px; max-height:440px; overflow:auto; margin:0; padding:.9rem; color:#4e627a; background:#fff; font: .72rem/1.65 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; white-space:pre-wrap; }
        .copilot-empty-state { display:flex; align-items:center; justify-content:center; gap:.65rem; min-height:270px; color:#74889e; font-size:.82rem; }.copilot-spinner { width:18px; height:18px; border:2px solid #d5e8f3; border-top-color:#0787d1; border-radius:50%; animation:spin .8s linear infinite; } @keyframes spin { to { transform:rotate(360deg); } }
        .copilot-brief-content { min-height:250px; margin-top:1.2rem; padding:1.15rem; color:#465b73; background:#f8fbfe; border:1px solid #e0eaf2; border-radius:10px; font-size:.86rem; line-height:1.75; white-space:pre-wrap; }.sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0; }
        @media (max-width: 780px) { .copilot-header, .copilot-panel-heading { align-items:stretch; flex-direction:column; }.copilot-tabs { align-self:flex-start; max-width:100%; overflow-x:auto; }.copilot-registers { grid-template-columns:1fr; }.copilot-message { max-width:92%; }.copilot-chat-topline { gap:.75rem; flex-direction:column; }.copilot-composer button span { display:none; } }
      `}</style>
    </div>
  );
}
