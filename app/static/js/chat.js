const chatBox = document.getElementById("chat-box");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

let isLoading = false;

if (!localStorage.getItem("user")) {
    window.location.href = "/login";
}

sendBtn.addEventListener("click", sendMessage);

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        if (isLoading) return;   // 🚨 block enter while loading
        sendMessage();
    }
});

function setLoading(state) {
    isLoading = state;
    sendBtn.disabled = state;

    sendBtn.innerText = state ? "Sending..." : "Send";
}

function showTypingIndicator() {
    const div = document.createElement("div");
    div.className = "bot-message typing-indicator";
    div.id = "typing-indicator";
    div.textContent = "MindCare AI is typing...";
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
}

async function sendMessage() {
    const message = input.value.trim();
    if (!message || isLoading) return; // 🚨 double safety

    addMessage(message, "user");
    input.value = "";

    setLoading(true);
    showTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        removeTypingIndicator();
        addMessage(data.response, "bot");

    } catch (err) {
        removeTypingIndicator();
        addMessage("Something went wrong. Please try again.", "bot");
        console.error(err);
    } finally {
        setLoading(false);
    }
}

function addMessage(text, sender) {
    const div = document.createElement("div");

    div.className =
        sender === "user"
            ? "user-message"
            : "bot-message";

    if (sender === "bot") {
        // ✅ Convert markdown → HTML
        div.innerHTML = marked.parse(text);
    } else {
        div.textContent = text;
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}