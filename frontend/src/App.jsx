import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const HISTORY_STORAGE_KEY = "incident_analyzer_history_v1";

function renderList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="muted">Not available</p>;
  }
  return (
    <ul className="list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function renderOrderedList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return <p className="muted">Not available</p>;
  }
  return (
    <ol className="list orderedList">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ol>
  );
}

function App() {
  const [description, setDescription] = useState("");
  const [logLine, setLogLine] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);
  const [history, setHistory] = useState([]);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [kbSummary, setKbSummary] = useState("");
  const [kbRootCause, setKbRootCause] = useState("");
  const [kbSeverity, setKbSeverity] = useState("");
  const [kbResolution, setKbResolution] = useState("");
  const [kbPreventive, setKbPreventive] = useState("");
  const [kbImpacted, setKbImpacted] = useState("");
  const [kbIndicators, setKbIndicators] = useState("");
  const [kbConfidence, setKbConfidence] = useState("");
  const [kbNotes, setKbNotes] = useState("");
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [followupQuestion, setFollowupQuestion] = useState("");
  const [followupMessages, setFollowupMessages] = useState([]);
  const [followupLoading, setFollowupLoading] = useState(false);
  const [followupError, setFollowupError] = useState("");

  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        setHistory(parsed);
      }
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  const canSubmit = useMemo(() => {
    return description.trim().length > 0 || logLine.trim().length > 0;
  }, [description, logLine]);
  const parsed = response?.parsed_output ?? null;

  async function onSubmit(event) {
    event.preventDefault();
    if (!canSubmit) {
      setError("Please enter description or log line.");
      return;
    }

    setLoading(true);
    setError("");
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          log_line: logLine.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Request failed.");
      }
      setResponse(data);
      const parsedOutput = data?.parsed_output ?? {};
      setKbSummary(parsedOutput.executive_summary || "");
      setKbRootCause(parsedOutput.root_cause || "");
      setKbSeverity(parsedOutput.severity || "");
      setKbResolution((parsedOutput.resolution_steps || []).join("\n"));
      setKbPreventive((parsedOutput.preventive_actions || []).join("\n"));
      setKbImpacted((parsedOutput.impacted_services || []).join(", "));
      setKbIndicators((parsedOutput.indicators_detected || []).join(", "));
      setKbConfidence(String(parsedOutput.confidence_score ?? ""));
      setKbNotes("");
      setSaveOpen(false);
      setSaveMessage("");
      setSaveError("");
      setFollowupMessages([]);
      setFollowupQuestion("");
      setFollowupError("");
      setHistory((prev) => {
        const item = {
          id: Date.now(),
          createdAt: new Date().toISOString(),
          description: description.trim(),
          logLine: logLine.trim(),
          response: data,
        };
        return [item, ...prev].slice(0, 12);
      });
    } catch (err) {
      setError(err.message || "Unexpected error.");
    } finally {
      setLoading(false);
    }
  }

  function onSelectHistory(item) {
    setDescription(item.description || "");
    setLogLine(item.logLine || "");
    setResponse(item.response || null);
    setError("");
    setFollowupMessages(item.followupMessages || []);
    setFollowupQuestion("");
    setFollowupError("");
  }

  function onClearHistory() {
    setHistory([]);
  }

  async function onLogFileUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      setError("Log file is too large. Max allowed size is 2 MB.");
      event.target.value = "";
      return;
    }

    try {
      const text = await file.text();
      setLogLine(text.slice(0, 20000));
      setUploadedFileName(file.name);
      setError("");
    } catch {
      setError("Unable to read the selected file. Please upload a text-based log file.");
    } finally {
      event.target.value = "";
    }
  }

  async function onSaveKnowledge() {
    if (!response) return;
    setSaveLoading(true);
    setSaveError("");
    setSaveMessage("");
    try {
      const payload = {
        description: description.trim(),
        log_line: logLine.trim(),
        notes: kbNotes.trim(),
        parsed_output: {
          executive_summary: kbSummary.trim(),
          root_cause: kbRootCause.trim(),
          severity: kbSeverity.trim(),
          impacted_services: kbImpacted
            .split(",")
            .map((v) => v.trim())
            .filter(Boolean),
          indicators_detected: kbIndicators
            .split(",")
            .map((v) => v.trim())
            .filter(Boolean),
          resolution_steps: kbResolution
            .split("\n")
            .map((v) => v.trim())
            .filter(Boolean),
          preventive_actions: kbPreventive
            .split("\n")
            .map((v) => v.trim())
            .filter(Boolean),
          confidence_score: Number(kbConfidence || 0),
        },
      };
      const res = await fetch(`${API_BASE_URL}/knowledge/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to save knowledge.");
      }
      setSaveMessage(`Saved to KB: ${data.id}`);
      setSaveOpen(false);
    } catch (err) {
      setSaveError(err.message || "Failed to save knowledge.");
    } finally {
      setSaveLoading(false);
    }
  }

  async function onFollowupSubmit(event) {
    event.preventDefault();
    if (!response || !followupQuestion.trim()) return;

    const userText = followupQuestion.trim();
    const nextHistory = [...followupMessages, { role: "user", content: userText }];
    setFollowupMessages(nextHistory);
    setFollowupQuestion("");
    setFollowupError("");
    setFollowupLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          log_line: logLine.trim(),
          parsed_output: response.parsed_output ?? null,
          raw_output: response.raw_output ?? "",
          question: userText,
          chat_history: nextHistory,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Follow-up failed.");
      }
      const assistantMsg = { role: "assistant", content: data.answer || "" };
      const updated = [...nextHistory, assistantMsg];
      setFollowupMessages(updated);
      setHistory((prev) =>
        prev.map((item) =>
          item.response === response ? { ...item, followupMessages: updated } : item
        )
      );
    } catch (err) {
      setFollowupError(err.message || "Follow-up failed.");
    } finally {
      setFollowupLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="layout">
        <aside className="historyPane">
          <div className="historyHeader">
            <h2>History</h2>
            <button type="button" className="historyClearBtn" onClick={onClearHistory} disabled={history.length === 0}>
              Clear
            </button>
          </div>

          {history.length === 0 ? (
            <p className="muted">No history yet.</p>
          ) : (
            <div className="historyList">
              {history.map((item) => {
                const summary =
                  item.response?.parsed_output?.executive_summary ||
                  item.response?.raw_output ||
                  "No summary";
                return (
                  <button
                    key={item.id}
                    type="button"
                    className="historyItem"
                    onClick={() => onSelectHistory(item)}
                  >
                    <span className="historyTime">
                      {new Date(item.createdAt).toLocaleString()}
                    </span>
                    <span className="historyText">{summary}</span>
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        <div className="card">
          <h1>DevOps Incident Analyzer</h1>
          <p className="subtitle">Submit incident description and logs to get RCA guidance.</p>

          <form onSubmit={onSubmit} className="form">
            <label>
              Incident Description
              <textarea
                rows={3}
                placeholder="Example: Users report HTTP 503 on payment API during peak traffic."
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </label>

            <label>
              Log Line / Snippet
              <textarea
                rows={5}
                placeholder="Example: DB timeout; connection pool usage 97%; pods restarting."
                value={logLine}
                onChange={(event) => setLogLine(event.target.value)}
              />
            </label>

            <label>
              Upload Log File
              <input
                type="file"
                accept=".log,.txt,.json,.out,.csv,text/plain,application/json"
                onChange={onLogFileUpload}
              />
              {uploadedFileName && (
                <span className="fileHint">Loaded: {uploadedFileName}</span>
              )}
            </label>

            <button type="submit" disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Incident"}
            </button>
          </form>

          {error && <div className="error">{error}</div>}

          {response && (
            <div className="result">
              <div className="resultHeader">
                <h2>{saveOpen ? "Edit Before Save" : "Analysis"}</h2>
                {!saveOpen && (
                  <button type="button" className="secondaryBtn" onClick={() => setSaveOpen(true)}>
                    Save To KB
                  </button>
                )}
              </div>

              {!saveOpen && (
                <>
                  {parsed ? (
                    <div className="analysisGrid">
                      <section className="panel panelWide">
                        <h3>Executive Summary</h3>
                        <p>{parsed.executive_summary || "Not available"}</p>
                      </section>

                      <section className="panel panelWide">
                        <h3>Root Cause</h3>
                        <p>{parsed.root_cause || "Not available"}</p>
                      </section>

                      <section className="panel panelWide panelImportant">
                        <h3>Resolution Steps</h3>
                        {renderOrderedList(parsed.resolution_steps)}
                      </section>

                      <section className="panel">
                        <h3>Severity</h3>
                        <span className={`severity severity-${String(parsed.severity || "").toLowerCase()}`}>
                          {parsed.severity || "Unknown"}
                        </span>
                      </section>

                      <section className="panel">
                        <h3>Confidence</h3>
                        <div className="confidenceWrap">
                          <div
                            className="confidenceBar"
                            style={{
                              width: `${Math.max(
                                0,
                                Math.min(100, Number(parsed.confidence_score ?? 0) * 100)
                              )}%`,
                            }}
                          />
                        </div>
                        <p className="muted">{Number(parsed.confidence_score ?? 0).toFixed(2)}</p>
                      </section>

                      <section className="panel">
                        <h3>Impacted Services</h3>
                        {renderList(parsed.impacted_services)}
                      </section>

                      <section className="panel">
                        <h3>Indicators Detected</h3>
                        {renderList(parsed.indicators_detected)}
                      </section>

                      <section className="panel">
                        <h3>Preventive Actions</h3>
                        {renderList(parsed.preventive_actions)}
                      </section>
                    </div>
                  ) : (
                    <p className="muted">No parsed output available. Showing raw output only.</p>
                  )}

                  <details className="rawBlock">
                    <summary>Raw Output</summary>
                    <pre>{response.raw_output}</pre>
                  </details>

                  <section className="followupPanel">
                    <h3>Follow-up Discussion</h3>
                    {followupMessages.length === 0 ? (
                      <p className="muted">
                        Ask a follow-up question about this incident analysis.
                      </p>
                    ) : (
                      <div className="chatList">
                        {followupMessages.map((msg, idx) => (
                          <div key={`${msg.role}-${idx}`} className={`chatBubble ${msg.role}`}>
                            <strong>{msg.role === "assistant" ? "Assistant" : "You"}:</strong>
                            <div className="chatContent">{msg.content}</div>
                          </div>
                        ))}
                      </div>
                    )}
                    <form onSubmit={onFollowupSubmit} className="followupForm">
                      <textarea
                        rows={2}
                        placeholder="Ask follow-up: e.g., Which metric should we alert on first?"
                        value={followupQuestion}
                        onChange={(e) => setFollowupQuestion(e.target.value)}
                      />
                      <button type="submit" disabled={followupLoading || !followupQuestion.trim()}>
                        {followupLoading ? "Replying..." : "Ask"}
                      </button>
                    </form>
                    {followupError && <div className="error">{followupError}</div>}
                  </section>
                </>
              )}

              {saveOpen && (
                <section className="savePanel">
                  <h3>Save Learned Solution to RAG</h3>
                  <div className="saveGrid">
                    <label>
                      Executive Summary
                      <textarea rows={3} value={kbSummary} onChange={(e) => setKbSummary(e.target.value)} />
                    </label>
                    <label>
                      Root Cause
                      <textarea rows={3} value={kbRootCause} onChange={(e) => setKbRootCause(e.target.value)} />
                    </label>
                    <label>
                      Severity
                      <input value={kbSeverity} onChange={(e) => setKbSeverity(e.target.value)} />
                    </label>
                    <label>
                      Confidence
                      <input value={kbConfidence} onChange={(e) => setKbConfidence(e.target.value)} />
                    </label>
                    <label>
                      Impacted Services (comma separated)
                      <input value={kbImpacted} onChange={(e) => setKbImpacted(e.target.value)} />
                    </label>
                    <label>
                      Indicators (comma separated)
                      <input value={kbIndicators} onChange={(e) => setKbIndicators(e.target.value)} />
                    </label>
                    <label>
                      Resolution Steps (one per line)
                      <textarea rows={4} value={kbResolution} onChange={(e) => setKbResolution(e.target.value)} />
                    </label>
                    <label>
                      Preventive Actions (one per line)
                      <textarea rows={4} value={kbPreventive} onChange={(e) => setKbPreventive(e.target.value)} />
                    </label>
                    <label>
                      Notes (optional)
                      <textarea rows={3} value={kbNotes} onChange={(e) => setKbNotes(e.target.value)} />
                    </label>
                  </div>
                  <div className="saveActions">
                    <button type="button" onClick={onSaveKnowledge} disabled={saveLoading}>
                      {saveLoading ? "Saving..." : "Submit to KB"}
                    </button>
                    <button type="button" className="secondaryBtn" onClick={() => setSaveOpen(false)} disabled={saveLoading}>
                      Cancel
                    </button>
                  </div>
                  {saveMessage && <div className="success">{saveMessage}</div>}
                  {saveError && <div className="error">{saveError}</div>}
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
