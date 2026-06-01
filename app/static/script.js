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
async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
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
        div.textContent = "[" + sessionLabel + "] " + m.content;
        div.style.cursor = "pointer";
        div.addEventListener("click", () => loadSession(m.session_id));
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