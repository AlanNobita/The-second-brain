let sessionId = null;
const messagesDiv = document.getElementById("messages");
const sessionListDiv = document.getElementById("session-list");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
function addMessage(role, content) {
    const div = document.createElement("div");
    div.className = "message " + role;
    div.textContent = content;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
async function handleYTCommand(command, args) {
    switch (command) {
        case "ytsearch": {
            const resp = await fetch("/yt/search?q=" + encodeURIComponent(args));
            const results = await resp.json();
            messagesDiv.innerHTML = "";
            addMessage("assistant", "━━━ YouTube Search Results ━━━");
            results.forEach((v, i) => {
                const div = document.createElement("div");
                div.className = "message assistant yt-result";
                div.innerHTML = "<strong>" + escapeHtml(String(i + 1) + ". " + v.title) + "</strong><br>" +
                    escapeHtml(v.channel) + " &middot; " + escapeHtml(v.published_at) + "<br>" +
                    '<a href="#" class="yt-ingest-link" data-url="' + escapeHtml(v.url) + '">📥 Ingest</a> &middot; ' +
                    '<a href="' + escapeHtml(v.url) + '" target="_blank">🔗 Watch</a>';
                const link = div.querySelector(".yt-ingest-link");
                link.addEventListener("click", async function(e) {
                    e.preventDefault();
                    addMessage("assistant", "📥 Ingesting video...");
                    try {
                        await fetch("/yt/ingest", {
                            method: "POST",
                            headers: {"Content-Type": "application/json"},
                            body: JSON.stringify({video_url: v.url})
                        });
                        addMessage("assistant", "✅ Video ingested!");
                    } catch (err) {
                        addMessage("assistant", "❌ Ingestion failed.");
                    }
                });
                messagesDiv.appendChild(div);
            });
            return true;
        }
        case "ytchannel": {
            addMessage("assistant", "📥 Fetching latest videos from channel...");
            try {
                const resp = await fetch("/yt/channel", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({channel_url: args})
                });
                const data = await resp.json();
                addMessage("assistant", "✅ Ingested " + data.ingested_count + " videos from channel.");
            } catch (err) {
                addMessage("assistant", "❌ Channel fetch failed.");
            }
            return true;
        }
        case "ytsub": {
            try {
                const resp = await fetch("/yt/subscribe", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({channel_url: args})
                });
                const data = await resp.json();
                addMessage("assistant", "✅ Subscribed to " + escapeHtml(data.channel_name) + ". Auto-ingesting every 6h.");
            } catch (err) {
                addMessage("assistant", "❌ Subscription failed.");
            }
            return true;
        }
        case "ytunsub": {
            try {
                const resp = await fetch("/yt/unsubscribe", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({sub_id: parseInt(args)})
                });
                const data = await resp.json();
                addMessage("assistant", data.status === "ok" ? "✅ Unsubscribed." : "❌ Not found.");
            } catch (err) {
                addMessage("assistant", "❌ Unsubscribe failed.");
            }
            return true;
        }
        case "ytsubs": {
            try {
                const resp = await fetch("/yt/subscriptions");
                const subs = await resp.json();
                messagesDiv.innerHTML = "";
                if (subs.length === 0) {
                    addMessage("assistant", "No active subscriptions.");
                    return true;
                }
                addMessage("assistant", "━━━ Subscriptions ━━━");
                subs.forEach(function(s) {
                    addMessage("assistant",
                        escapeHtml(s.channel_name) + "\n" +
                        "Last checked: " + (s.last_checked || "never") + "\n" +
                        "ID: " + s.id
                    );
                });
            } catch (err) {
                addMessage("assistant", "❌ Failed to list subscriptions.");
            }
            return true;
        }
        default:
            return false;
    }
}

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Check for YT commands
    if (text.startsWith("/")) {
        const spaceIdx = text.indexOf(" ");
        const command = spaceIdx === -1 ? text.slice(1) : text.slice(1, spaceIdx);
        const args = spaceIdx === -1 ? "" : text.slice(spaceIdx + 1);
        const handled = await handleYTCommand(command, args);
        if (handled) {
            input.value = "";
            return;
        }
    }

    // Normal chat flow
    addMessage("user", text);
    input.value = "";
    sendBtn.disabled = true;
    showTypingIndicator();
    try {
        const response = await fetch("/chat/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId })
        });
        const data = await response.json();
        sessionId = data.session_id;
        removeTypingIndicator();
        addMessage("assistant", data.reply);
        loadSessions();
    } catch (err) {
        removeTypingIndicator();
        addMessage("assistant", "Error: could not reach the server.");
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}
async function loadSessions() {
    const response = await fetch("/sessions");
    const sessions = await response.json();
    sessionListDiv.innerHTML = "";
    sessions.forEach(s => {
        const item = document.createElement("div");
        item.className = "session-item" + (s.session_id === sessionId ? " active" : "");
        item.innerHTML = `
            <div>${escapeHtml(s.title || "(empty)")}</div>
            <div class="count">${s.message_count} messages</div>
        `;
        item.addEventListener("click", () => loadSession(s.session_id));
        sessionListDiv.appendChild(item);
    });
}
async function loadSession(id) {
    sessionId = id;
    const response = await fetch("/chat/history?session_id=" + id);
    const data = await response.json();
    messagesDiv.innerHTML = "";
    data.messages.forEach(m => addMessage(m.role, m.content));
    loadSessions();
}
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});
loadSessions();

const searchInput = document.getElementById("search-input");

async function performSearch(query) {
    const response = await fetch("/search?q=" + encodeURIComponent(query))
    const results = await response.json();
    messagesDiv.innerHTML = "";
    if (results.length === 0) { 
        addMessage("assistant", "No messages found for \"" + query + "\"");
        return ;
    }
    addMessage("assistant", "Search results for \"" + query + "\"")
    results.forEach(m => {
        const sessionLabel = "Session: " + m.session_id.slice(0, 8) + "...";
        const div = document.createElement("div");
        div.className = "message " + m.role;
        div.style.cursor = "pointer";
        div.addEventListener("click", () => loadSession(m.session_id));
        const source = m._source || "semantic";
        const badge = document.createElement("span");
        badge.className = "result-source";
        badge.textContent = source;
        const textSpan = document.createElement("span");
        textSpan.textContent = "[" + sessionLabel + "] " + m.content;
        div.appendChild(badge);
        div.appendChild(textSpan);
        messagesDiv.appendChild(div);
    })
}

function showTypingIndicator() {
    const div = document.createElement("div");
    div.className = "message assistant typing";
    div.id = "typing-indicator";
    div.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
function removeTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();
}

searchInput.addEventListener("input", (e) =>{
    const query = e.target.value.trim();
    if (query) performSearch(query);
    else loadSessions();
})