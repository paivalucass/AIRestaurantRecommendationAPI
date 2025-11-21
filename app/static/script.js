function getLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            document.getElementById("lat").value = pos.coords.latitude.toFixed(6);
            document.getElementById("lon").value = pos.coords.longitude.toFixed(6);
        },
        (err) => {
            alert("Unable to retrieve your location. " + err.message);
        }
    );
}

async function sendChat() {
    const query = document.getElementById("chat-query").value.trim();
    const lat = parseFloat(document.getElementById("lat").value);
    const lon = parseFloat(document.getElementById("lon").value);
    const chatLog = document.getElementById("chat-log");

    if (!query) return;

    // USER MESSAGE
    const userDiv = document.createElement("div");
    userDiv.className = "chat-message chat-user";
    userDiv.textContent = query;
    chatLog.appendChild(userDiv);
    chatLog.scrollTop = chatLog.scrollHeight;

    document.getElementById("chat-query").value = "";

    // AI TYPING PLACEHOLDER
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "chat-message chat-bot loading";
    loadingDiv.innerHTML = `
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
    `;
    chatLog.appendChild(loadingDiv);
    chatLog.scrollTop = chatLog.scrollHeight;

    // API REQUEST
    const res = await fetch(
        `/chat?query=${encodeURIComponent(query)}&user_lat=${lat}&user_lon=${lon}&radius=20000`
    );

    const data = await res.json();

    // REMOVE LOADING AND REPLACE WITH AI ANSWER
    loadingDiv.remove();

    const botDiv = document.createElement("div");
    botDiv.className = "chat-message chat-bot";
    botDiv.textContent = data.response;
    chatLog.appendChild(botDiv);

    chatLog.scrollTop = chatLog.scrollHeight;
}
