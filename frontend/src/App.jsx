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
  }

  function onClearHistory() {
    setHistory([]);
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

            <button type="submit" disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Incident"}
            </button>
          </form>

          {error && <div className="error">{error}</div>}

          {response && (
            <div className="result">
              <h2>Analysis</h2>

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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
