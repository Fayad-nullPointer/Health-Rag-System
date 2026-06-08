const chatBox = document.getElementById("chat-box");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");

let isLoading = false;

if (!localStorage.getItem("user")) {
    window.location.href = "/login";
}

sendBtn.addEventListener("click", sendMessage);

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
    if (!message || isLoading) return;

    const token = localStorage.getItem("token");

    addMessage(message, "user");
    input.value = "";

    setLoading(true);
    showTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        console.log("Status:", response.status);
        console.log("Response:", data);

        removeTypingIndicator();

        if (!response.ok) {
            addMessage(data.detail || "Authentication failed", "bot");
            return;
        }

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
        div.innerHTML = marked.parse(text || "");
    } else {
        div.textContent = text || "";
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
});

input.addEventListener("keydown", (e) => {
    if (isLoading) return;

    // ENTER → send message
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault(); // stop newline
        sendMessage();
    }

    // SHIFT + ENTER → allow newline (do nothing)
});

// =========================================================
// VOICE RECORDING
// =========================================================

const micBtn = document.getElementById("mic-btn");
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

micBtn.addEventListener("click", toggleRecording);

async function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm'
        });

        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                audioChunks.push(e.data);
            }
        };

        mediaRecorder.onstop = async () => {
            // Stop all tracks to release mic
            stream.getTracks().forEach(track => track.stop());

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

            if (audioBlob.size < 1000) {
                addMessage("Recording too short. Please try again.", "bot");
                return;
            }

            await sendVoiceMessage(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add("recording");
        micBtn.textContent = "⏹";

        // Auto-stop after 60 seconds
        setTimeout(() => {
            if (isRecording) {
                stopRecording();
            }
        }, 60000);

    } catch (err) {
        console.error("Microphone access denied:", err);
        addMessage("Microphone access denied. Please allow microphone permissions.", "bot");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.textContent = "🎤";
}

async function sendVoiceMessage(audioBlob) {
    const token = localStorage.getItem("token");

    addMessage("🎤 Voice message sent...", "user");

    setLoading(true);
    showTypingIndicator();

    try {
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");

        const response = await fetch("/voice", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        console.log("Voice Status:", response.status);
        console.log("Voice Response:", data);

        removeTypingIndicator();

        if (!response.ok) {
            addMessage(data.detail || "Voice processing failed", "bot");
            return;
        }

        // Show what was transcribed
        if (data.transcribed_text) {
            // Replace the placeholder message with actual transcription
            const messages = chatBox.querySelectorAll(".user-message");
            const lastUserMsg = messages[messages.length - 1];
            if (lastUserMsg && lastUserMsg.textContent.includes("Voice message sent")) {
                lastUserMsg.innerHTML = `🎤 <em>"${data.transcribed_text}"</em>`;
            }
        }

        addMessage(data.response, "bot");

    } catch (err) {
        removeTypingIndicator();
        addMessage("Voice processing failed. Please try again.", "bot");
        console.error(err);
    } finally {
        setLoading(false);
    }
}