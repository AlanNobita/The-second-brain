let sessionId = null;
        const messagesDiv = document.getElementById("messages");
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
            try {
                const response = await fetch("/chat/send", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, session_id: sessionId })
                });
                const data = await response.json();
                sessionId = data.session_id;
                addMessage("assistant", data.reply);
            } catch (err) {
                addMessage("assistant", "Error: could not reach the server.");
            } finally {
                sendBtn.disabled = false;
                input.focus();
            }
        }
        sendBtn.addEventListener("click", sendMessage);
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendMessage();
        });