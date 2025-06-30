// === Global States ===
let micEnabled = false;
let audioMuted = false;
let forgotPasswordUsername = '';

// === Speech Recognition Setup ===
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;

if (recognition) {
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = true;

    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript;
        document.getElementById("user-input").value = transcript;
        sendMessage();
    };

    recognition.onend = () => {
        if (micEnabled) recognition.start();
        else updateMicUI(false);
    };
}

// === DOM Elements ===
const micBtn = document.getElementById("mic-toggle");
const micIcon = document.getElementById("mic-icon");
const micStatus = document.getElementById("mic-status");
const settingsToggle = document.getElementById("settings-toggle");
const settingsMenu = document.getElementById("settings-menu");
const userInput = document.getElementById("user-input");
const chatBox = document.getElementById("chat-box");

// === Mic Toggle ===
micBtn?.addEventListener("click", () => {
    if (!recognition) return alert("⚠️ Speech Recognition not supported.");
    micEnabled = !micEnabled;
    micEnabled ? recognition.start() : recognition.stop();
    updateMicUI(micEnabled);
});

function updateMicUI(on) {
    micIcon.src = on ? "/static/images/mic_off.png" : "/static/images/mic_on.png";
    micStatus.textContent = on ? "Mic is On" : "Mic is Off";
}

// === Chat Functions ===
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    const noChatMsg = document.querySelector(".no-chat");
    if (noChatMsg) noChatMsg.style.display = "none";

    appendUserMessage(text);
    userInput.value = "";

    const typing = document.createElement("div");
    typing.className = "bot-message";
    typing.id = "typing-indicator";
    typing.innerHTML = `<b>Jarvis:</b> <i>Typing...</i>`;
    chatBox.appendChild(typing);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        updateTypingIndicator(data.response);

        const lower = data.response.toLowerCase();
        const isAutomation = ["opening", "launching", "muting", "closing", "setting reminder", "volume", "brightness"]
            .some(kw => lower.includes(kw));

        if (!audioMuted && !isAutomation) {
            const tts = await fetch("/speak", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: data.response })
            });
            if (tts.ok) {
                const blob = await tts.blob();
                new Audio(URL.createObjectURL(blob)).play();
            }
        }
    } catch {
        document.getElementById("typing-indicator")?.remove();
        appendBotMessage("❌ Failed to connect to server.");
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendUserMessage(txt) {
    const d = document.createElement("div");
    d.className = "user-message";
    d.innerHTML = `<b>You:</b> ${escapeHtml(txt)}`;
    chatBox.appendChild(d);
}

function appendBotMessage(txt) {
    const d = document.createElement("div");
    d.className = "bot-message";
    d.innerHTML = `<b>Jarvis:</b> ${escapeHtml(txt)}`;
    chatBox.appendChild(d);
}

function updateTypingIndicator(txt) {
    const el = document.getElementById("typing-indicator");
    if (el) {
        el.innerHTML = `<b>Jarvis:</b> ${txt}`;
        el.removeAttribute("id");
    }
}

function escapeHtml(s) {
    return s.replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
}

userInput.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

// === Settings Panel ===
settingsToggle?.addEventListener("click", () => {
    settingsMenu?.classList.toggle("hidden");
});

function toggleAudio() {
    audioMuted = !audioMuted;
    document.getElementById("audio-state").textContent = audioMuted ? "Mute" : "Unmute";
}

// === Signup ===
async function submitSignup() {
    const usr = document.getElementById("signup-username").value.trim();
    const email = document.getElementById("signup-email").value.trim();
    const pwd = document.getElementById("signup-password").value.trim();

    if (!usr || !email || !pwd) return showMessage("❌ All fields are required.");

    try {
        const res = await fetch("/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: usr, email, password: pwd })
        });
        const data = await res.json();
        showMessage(data.message);
        if (res.ok) location.reload();
    } catch {
        showMessage("❌ Signup failed. Try again.");
    }
}

// === Login ===
async function submitLogin() {
    const iden = document.getElementById("login-identifier").value.trim();
    const pwd = document.getElementById("login-password").value.trim();

    if (!iden || !pwd) return showMessage("❌ All fields are required.");

    try {
        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identifier: iden, password: pwd })
        });
        const data = await res.json();
        showMessage(data.message);
        if (res.ok) location.reload();
    } catch {
        showMessage("❌ Login failed. Try again.");
    }
}

// === Forgot Password Flow ===
function showForgotPasswordForm(e) {
    e.preventDefault();
    hideForms();
    document.getElementById("forgot-password-form").classList.remove("hidden");
}

async function submitForgotPassword() {
    const usr = document.getElementById("fp-identifier").value.trim();
    if (!usr) return alert("Enter username.");

    forgotPasswordUsername = usr;
    try {
        const res = await fetch("/forgot_password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: usr })
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            hideForms();
            document.getElementById("otp-verification-form").classList.remove("hidden");
        } else alert(data.message);
    } catch {
        alert("Network error sending OTP.");
    }
}

async function submitOTP() {
    const otp = document.getElementById("otp-input").value.trim();
    if (!otp) return alert("Enter OTP.");

    try {
        const res = await fetch("/verify_otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: forgotPasswordUsername, otp })
        });
        const data = await res.json();
        if (res.ok) {
            alert("✅ OTP valid. Reset your password now.");
            hideForms();
            document.getElementById("reset-password-form").classList.remove("hidden");
        } else {
            alert(data.message);
        }
    } catch {
        alert("❌ Network error verifying OTP.");
    }
}

async function submitNewPassword() {
    const pwd = document.getElementById("new-password").value.trim();
    if (!pwd) return alert("Enter a new password.");

    try {
        const res = await fetch("/reset_password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: forgotPasswordUsername,
                otp: document.getElementById("otp-input").value.trim(),
                new_password: pwd
            })
        });
        const data = await res.json();
        showMessage(data.message);
        if (res.ok) {
            hideForms();
            document.getElementById("login-form").classList.remove("hidden");
        }
    } catch {
        showMessage("❌ Password reset failed.");
    }
}

// === Modal Snackbar ===
function showMessage(msg) {
    const m = document.getElementById("messageModal");
    document.getElementById("modalMessage").textContent = msg;
    m.style.display = "flex";
    setTimeout(() => m.style.display = "none", 3000);
}
function closeModal() {
    document.getElementById("messageModal").style.display = "none";
}

// === Logout ===
function logout() {
    fetch("/logout", { method: "POST" }).then(() => {
        chatBox.innerHTML = "";
        showMessage("👋 Logged out.");
        location.reload();
    });
}

// === Form Control ===
function signup() {
    hideForms();
    document.getElementById("signup-form").classList.remove("hidden");
}
function login() {
    hideForms();
    document.getElementById("login-form").classList.remove("hidden");
}
function hideForms() {
    document.querySelectorAll(".auth-form").forEach(el => el.classList.add("hidden"));
}

// === Load User Badge ===
window.onload = async () => {
    chatBox.scrollTop = chatBox.scrollHeight;
    try {
        const res = await fetch("/get_active_user");
        const data = await res.json();
        if (data.username) {
            const b = document.getElementById("user-badge");
            b.textContent = data.username[0].toUpperCase();
            b.style.display = "flex";

            if (data.username === "admin") {
                document.getElementById("admin-btn")?.classList.remove("hidden");
                loadAdminUsers(); // Load admin dashboard on load if present
            }
        }
    } catch {}
};

// === Admin Dashboard Functions ===
async function loadAdminUsers() {
    try {
        const res = await fetch("/admin/users");
        const data = await res.json();
        const list = document.getElementById("user-list");
        list.innerHTML = "";

        data.users.forEach(user => {
            const row = document.createElement("div");
            row.className = "user-row";
            row.innerHTML = `
                <span>${user.username}</span>
                <button onclick="deleteUser('${user.username}')">Delete</button>
            `;
            list.appendChild(row);
        });
    } catch {
        alert("❌ Failed to load user list.");
    }
}

async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;
    try {
        const res = await fetch("/admin/delete_user", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username })
        });
        const data = await res.json();
        showMessage(data.message);
        if (res.ok) loadAdminUsers();
    } catch {
        showMessage("❌ Failed to delete user.");
    }
}

// === Form Submit Bindings ===
document.getElementById("signup-form")?.addEventListener("submit", e => {
    e.preventDefault();
    submitSignup();
});
document.getElementById("login-form")?.addEventListener("submit", e => {
    e.preventDefault();
    submitLogin();
});

