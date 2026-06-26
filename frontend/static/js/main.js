document.addEventListener("DOMContentLoaded", function () {
    loadHistory();
    loadDocuments();
    checkHealth();
    setInterval(loadDocuments, 3000);
    setInterval(checkHealth, 10000);

    const uploadForm = document.getElementById("upload-form");
    const uploadStatus = document.getElementById("upload-status");

    if (uploadForm) {
        uploadForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const formData = new FormData(this);
            const btn = this.querySelector("button[type=submit]");
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Uploading...';

            uploadStatus.innerHTML = '<div class="status-box info"><span class="status-icon">&#9432;</span> Saving file and queuing for background indexing...</div>';

            try {
                const resp = await fetch("/documents/upload", { method: "POST", body: formData });
                const data = await resp.json();
                if (resp.ok) {
                    uploadStatus.innerHTML = `<div class="status-box success"><span class="status-icon">&#10003;</span> <strong>Uploaded.</strong> Indexing in background (ID: ${data.document_id}).</div>`;
                    btn.innerHTML = "Upload &amp; Index";
                    loadDocuments();
                    pollDocumentStatus(data.document_id);
                } else {
                    uploadStatus.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> ${data.detail || "Upload failed."}</div>`;
                }
            } catch (err) {
                uploadStatus.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Connection error: ${err.message}</div>`;
            }
            btn.disabled = false;
            btn.innerHTML = "Upload &amp; Index";
        });
    }

    const researchForm = document.getElementById("research-form");
    const researchStatus = document.getElementById("research-status");
    let currentResearchAbort = null;

    async function autoCancelPreviousRun() {
        try {
            const resp = await fetch("/history");
            const runs = await resp.json();
            const running = runs.find(r => r.status === "running");
            if (running) {
                await fetch(`/research/${running.id}/cancel`, { method: "POST" });
            }
        } catch (_) {}
    }

    if (researchForm) {
        researchForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            // Abort any previous stream and cancel old run
            if (currentResearchAbort) {
                currentResearchAbort.abort();
                currentResearchAbort = null;
            }
            await autoCancelPreviousRun();

            const question = document.getElementById("question").value;
            const btn = this.querySelector("button[type=submit]");
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Running...';

            const statusBox = document.getElementById("research-status");
            const timeline = document.getElementById("agent-timeline");
            statusBox.innerHTML = '<div class="status-box info"><span class="status-icon">&#9432;</span> <span id="research-progress">Starting...</span> <button id="cancel-research-btn" class="btn btn-sm btn-secondary" style="margin-left:8px;" onclick="cancelResearch()">Cancel</button></div>';
            timeline.style.display = "block";
            timeline.innerHTML = "";
            let llmModel = "mistral:7b";

            const abortController = new AbortController();
            currentResearchAbort = abortController;

            try {
                const resp = await fetch("/research/stream", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: "question=" + encodeURIComponent(question),
                    signal: abortController.signal,
                });

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";
                let researchId = null;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split("\n");
                    buffer = lines.pop() || "";

                    let eventType = "";
                    for (const line of lines) {
                        if (line.startsWith("event: ")) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith("data: ")) {
                            const data = line.slice(6).trim();
                            if (eventType === "config") {
                                const c = JSON.parse(data);
                                llmModel = c.primary;
                            } else if (eventType === "agent") {
                                document.getElementById("research-progress").textContent = data;
                            } else if (eventType === "status") {
                                document.getElementById("research-progress").textContent = data;
                            } else if (eventType === "agent_start") {
                                const info = JSON.parse(data);
                                addAgentStep(timeline, info.name, llmModel);
                            } else if (eventType === "agent_done") {
                                const info = JSON.parse(data);
                                completeAgentStep(timeline, info.name, info.duration, info.llm || null);
                            } else if (eventType === "agent_error") {
                                const info = JSON.parse(data);
                                failAgentStep(timeline, info.name, info.error);
                            } else if (eventType === "done") {
                                researchId = data;
                            } else if (eventType === "cancelled") {
                                timeline.querySelectorAll(".agent-step.running").forEach(el => {
                                    el.className = "agent-step cancelled";
                                    el.querySelector(".agent-status").textContent = "—";
                                });
                                statusBox.innerHTML = `<div class="status-box warning"><span class="status-icon">&#9888;</span> ${data}</div>`;
                            } else if (eventType === "error") {
                                statusBox.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> ${data}</div>`;
                            }
                        }
                    }
                }

                if (researchId) {
                    statusBox.innerHTML = `<div class="status-box success"><span class="status-icon">&#10003;</span> <strong>Research complete!</strong> <a href="/research/${researchId}/report.html" style="color:var(--primary);font-weight:500;">View the full report &rarr;</a></div>`;
                    loadHistory();
                } else if (timeline.querySelector(".agent-step.cancelled")) {
                    // already handled above
                } else {
                    statusBox.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Research failed to complete.</div>`;
                }
            } catch (err) {
                if (err.name === "AbortError") {
                    statusBox.innerHTML = `<div class="status-box warning"><span class="status-icon">&#9888;</span> Previous research cancelled.</div>`;
                } else {
                    statusBox.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Connection error: ${err.message}</div>`;
                }
            }
            if (currentResearchAbort === abortController) {
                currentResearchAbort = null;
            }
            btn.disabled = false;
            btn.innerHTML = "Start Research";
        });
    }

    function addAgentStep(timeline, name, model) {
        const step = document.createElement("div");
        step.className = "agent-step running";
        step.dataset.name = name;
        step.innerHTML = `<div class="agent-step-header">
            <span class="agent-status"><span class="spinner"></span></span>
            <span class="agent-name">${name}</span>
            <span class="agent-model">${model}</span>
        </div>
        <div class="agent-step-details">
            <span class="agent-metric">Running...</span>
        </div>`;
        timeline.appendChild(step);
        timeline.scrollTop = timeline.scrollHeight;
    }

    function completeAgentStep(timeline, name, duration, llm) {
        const step = timeline.querySelector(`.agent-step[data-name="${name}"]`);
        if (!step) return;
        step.className = "agent-step done";
        step.querySelector(".agent-status").textContent = "✓";
        let details = `<span class="agent-metric">${duration}s</span>`;
        if (llm) {
            details += ` <span class="agent-metric">${llm.response_len} chars</span> <span class="agent-metric">${llm.duration}s LLM</span>`;
        }
        step.querySelector(".agent-step-details").innerHTML = details;
    }

    function failAgentStep(timeline, name, error) {
        const step = timeline.querySelector(`.agent-step[data-name="${name}"]`);
        if (!step) return;
        step.className = "agent-step error";
        step.querySelector(".agent-status").textContent = "✗";
        step.querySelector(".agent-step-details").innerHTML = `<span class="agent-metric" style="color:var(--error)">${error}</span>`;
    }

    async function pollDocumentStatus(docId) {
        for (let i = 0; i < 120; i++) {
            await sleep(1500);
            try {
                const resp = await fetch(`/documents/${docId}`);
                const doc = await resp.json();
                if (doc.status === "ready" || doc.status === "failed") {
                    loadDocuments();
                    const container = document.getElementById("upload-status");
                    if (doc.status === "ready") {
                        container.innerHTML = `<div class="status-box success"><span class="status-icon">&#10003;</span> <strong>Indexing complete.</strong> ${doc.chunk_count} chunks indexed for <em>${escapeHtml(doc.filename)}</em>.</div>`;
                    } else {
                        const errMsg = doc.error ? `: ${escapeHtml(doc.error)}` : "";
                        container.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Indexing failed for <em>${escapeHtml(doc.filename)}</em>${errMsg}</div>`;
                    }
                    return;
                }
                loadDocuments();
            } catch (_) {}
        }
    }

    async function loadDocuments() {
        const container = document.getElementById("documents-list");
        const countBadge = document.getElementById("documents-count");
        if (!container) return;

        try {
            const resp = await fetch("/documents");
            const docs = await resp.json();
            if (!docs.length) {
                container.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128196;</div><p>No documents uploaded yet.</p></div>';
                if (countBadge) countBadge.textContent = "0";
                return;
            }
            if (countBadge) countBadge.textContent = docs.length;

            let html = '<div class="table-container"><table><thead><tr><th>File</th><th>Company</th><th>Status</th><th>Chunks</th><th>Date</th><th></th></tr></thead><tbody>';
            for (const d of docs) {
                const statusLabel = d.status.charAt(0).toUpperCase() + d.status.slice(1);
                const errorTip = d.error ? ` title="${escapeHtml(d.error)}"` : "";
                html += `<tr${errorTip}>
                    <td>${escapeHtml(d.filename)}${d.error ? ' <span style="color:var(--error);cursor:help;" title="' + escapeHtml(d.error) + '">&#9888;</span>' : ""}</td>
                    <td>${d.company || "&mdash;"}</td>
                    <td><span class="status-badge ${d.status}">${statusLabel}</span></td>
                    <td>${d.status === "processing" && d.chunk_count ? d.processed_chunks + " / " + d.chunk_count : (d.chunk_count || 0)}</td>
                    <td style="color:var(--text-secondary);font-size:0.8rem;">${d.uploaded_at ? d.uploaded_at.substring(0, 10) : "&mdash;"}</td>
                    <td><button class="btn btn-sm btn-secondary" onclick="deleteDocument(${d.id}, '${escapeHtml(d.filename)}')">Delete</button></td>
                </tr>`;
            }
            html += "</tbody></table></div>";
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Failed to load: ${err.message}</div>`;
        }
    }

    async function loadHistory() {
        const container = document.getElementById("recent-reports");
        const countBadge = document.getElementById("history-count");
        if (!container) return;

        try {
            const resp = await fetch("/history");
            const runs = await resp.json();
            if (!runs.length) {
                container.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128202;</div><p>No reports yet. Upload documents and start a research inquiry.</p></div>';
                if (countBadge) countBadge.textContent = "0";
                return;
            }
            if (countBadge) countBadge.textContent = runs.length;

            let html = '<div class="table-container"><table><thead><tr><th>ID</th><th>Question</th><th>Status</th><th>Date</th><th></th></tr></thead><tbody>';
            for (const r of runs) {
                const label = r.status.charAt(0).toUpperCase() + r.status.slice(1);
                html += `<tr>
                    <td style="font-weight:600;color:var(--text-secondary);">#${r.id}</td>
                    <td>${escapeHtml(r.question.substring(0, 80))}${r.question.length > 80 ? "..." : ""}</td>
                    <td><span class="status-badge ${r.status}">${label}</span></td>
                    <td style="color:var(--text-secondary);font-size:0.8rem;">${r.created_at ? r.created_at.substring(0, 10) : "&mdash;"}</td>
                    <td>${r.status === "completed" ? `<a href="/research/${r.id}/report.html" class="btn btn-secondary btn-sm">View</a>` : `<span style="color:var(--text-muted);font-size:0.8rem;">${r.status}</span>`}</td>
                </tr>`;
            }
            html += "</tbody></table></div>";
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> Failed to load history: ${err.message}</div>`;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    async function checkHealth() {
        const dot = document.getElementById("health-dot");
        const text = document.getElementById("health-text");
        if (!dot || !text) return;
        try {
            const resp = await fetch("/health");
            const h = await resp.json();
            const allOk = h.app === "ok" && h.qdrant === "ok" && h.ollama && h.ollama.startsWith("ok") && h.database === "ok";
            dot.className = "status-dot" + (allOk ? "" : " offline");
            text.textContent = allOk ? "All systems ok" : h.qdrant !== "ok" ? "Qdrant offline" : h.ollama && !h.ollama.startsWith("ok") ? "Ollama offline" : "Issues detected";
        } catch (_) {
            dot.className = "status-dot offline";
            text.textContent = "Server unreachable";
        }
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    window.deleteDocument = async function (docId, filename) {
        if (!confirm(`Delete "${filename}"? This will remove the file and its indexed vectors.`)) return;
        try {
            const resp = await fetch(`/documents/${docId}`, { method: "DELETE" });
            const data = await resp.json();
            if (resp.ok) {
                loadDocuments();
            } else {
                alert(`Delete failed: ${data.detail}`);
            }
        } catch (err) {
            alert(`Delete failed: ${err.message}`);
        }
    };

    window.cancelResearch = async function () {
        if (currentResearchAbort) {
            currentResearchAbort.abort();
            currentResearchAbort = null;
        }
        try {
            const resp = await fetch("/history");
            const runs = await resp.json();
            const running = runs.find(r => r.status === "running");
            if (running) {
                await fetch(`/research/${running.id}/cancel`, { method: "POST" });
            }
        } catch (_) {}
    };

    window.startAsyncResearch = async function () {
        const question = document.getElementById("question").value;
        if (!question.trim()) return;
        const btn = document.getElementById("async-research-btn");
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Starting...';

        const statusBox = document.getElementById("research-status");
        try {
            const formData = new FormData();
            formData.append("question", question);
            const resp = await fetch("/research/async", { method: "POST", body: formData });
            const data = await resp.json();
            if (resp.ok) {
                statusBox.innerHTML = `<div class="status-box info"><span class="status-icon">&#9432;</span> Research started in background (ID: #${data.research_id}). <a href="/research/${data.research_id}/report.html" style="color:var(--primary);">Check results &rarr;</a></div>`;
                loadHistory();
            } else {
                statusBox.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> ${data.detail || "Failed to start research."}</div>`;
            }
        } catch (err) {
            statusBox.innerHTML = `<div class="status-box error"><span class="status-icon">&#10007;</span> ${err.message}</div>`;
        }
        btn.disabled = false;
        btn.innerHTML = "Start Async \u2192";
    };

    window.toggleCollapse = function (id) {
        const content = document.getElementById(id);
        const icon = document.getElementById(id + "-icon");
        if (!content) return;
        const wasCollapsed = content.classList.toggle("collapsed");
        if (icon) icon.classList.toggle("collapsed");
        localStorage.setItem("collapse-" + id, wasCollapsed ? "1" : "0");
    };

    (function restoreCollapse() {
        const els = document.querySelectorAll(".collapse-content");
        els.forEach(el => {
            const key = "collapse-" + el.id;
            if (localStorage.getItem(key) === "1") {
                el.classList.add("collapsed");
                const icon = document.getElementById(el.id + "-icon");
                if (icon) icon.classList.add("collapsed");
            }
        });
    })();
});
