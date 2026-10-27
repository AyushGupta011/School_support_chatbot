from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

@router.get("/")
async def get_ui():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apex University — Academic Portal & AI Copilot</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-canvas: #F8FAFC;
            --bg-card: #FFFFFF;
            --bg-subtle: #F1F5F9;
            --border: #E2E8F0;
            --border-hover: #CBD5E1;
            --text-primary: #0F172A;
            --text-secondary: #475569;
            --text-muted: #94A3B8;
            --accent-black: #0F172A;
            --accent-emerald: #10B981;
            --accent-rose: #EF4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        header {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border);
            padding: 0.85rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .crest-icon {
            width: 32px;
            height: 32px;
            background: #0F172A;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 0.9rem;
        }

        .brand h1 {
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .brand span {
            font-size: 0.68rem;
            color: var(--text-muted);
            display: block;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #FFFFFF;
            border: 1px solid var(--border);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--accent-emerald);
        }

        .container {
            max-width: 920px;
            width: 100%;
            margin: 0 auto;
            padding: 1.5rem;
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        /* Login Card */
        #login-section {
            max-width: 440px;
            margin: 3.5rem auto;
            width: 100%;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2.25rem;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
        }

        .login-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }

        .login-subtitle {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 1.5rem;
        }

        .presets-label {
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
        }

        .presets-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-bottom: 1.25rem;
        }

        .preset-btn {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.6rem;
            text-align: left;
            cursor: pointer;
            transition: all 0.15s;
        }

        .preset-btn:hover, .preset-btn.active {
            border-color: var(--accent-black);
            background: var(--bg-subtle);
        }

        .preset-name {
            font-size: 0.74rem;
            font-weight: 700;
            color: var(--text-primary);
            display: block;
        }

        .preset-role {
            font-size: 0.64rem;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
        }

        .form-group {
            margin-bottom: 1rem;
        }

        .form-label {
            display: block;
            font-size: 0.74rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 0.35rem;
        }

        .input-field {
            width: 100%;
            background: var(--bg-canvas);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
            color: var(--text-primary);
            font-size: 0.875rem;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s;
        }

        .input-field:focus {
            border-color: var(--accent-black);
            background: #FFFFFF;
        }

        .btn-primary {
            width: 100%;
            background: #0F172A;
            color: #FFFFFF;
            font-weight: 600;
            font-size: 0.875rem;
            border: none;
            border-radius: 12px;
            padding: 0.8rem;
            cursor: pointer;
            margin-top: 0.5rem;
            transition: background 0.15s;
        }

        .btn-primary:hover {
            background: #1E293B;
        }

        #error {
            background: #FEF2F2;
            border: 1px solid #FECACA;
            color: #B91C1C;
            padding: 0.65rem 0.85rem;
            border-radius: 10px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
            display: none;
        }

        /* Chat Section */
        #chat-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 16px;
        }

        .student-pill {
            display: flex;
            align-items: center;
            gap: 0.65rem;
        }

        .student-avatar {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.75rem;
            color: var(--text-primary);
        }

        .student-info {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .student-sub {
            font-size: 0.68rem;
            color: var(--text-secondary);
        }

        .btn-logout {
            background: #FFFFFF;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            border-radius: 8px;
            padding: 0.35rem 0.75rem;
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }

        .btn-logout:hover {
            background: #FEF2F2;
            color: #DC2626;
            border-color: #FECACA;
        }

        .prompt-pills {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.25rem;
        }

        .pill-btn {
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 9999px;
            padding: 0.35rem 0.85rem;
            font-size: 0.74rem;
            font-weight: 500;
            color: var(--text-secondary);
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.15s;
        }

        .pill-btn:hover {
            border-color: var(--accent-black);
            color: var(--text-primary);
        }

        #chat {
            flex: 1;
            height: 480px;
            overflow-y: auto;
            border: 1px solid var(--border);
            background: #FFFFFF;
            border-radius: 20px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .msg-wrap {
            display: flex;
            flex-direction: column;
            max-width: 82%;
        }

        .msg-wrap.user {
            align-self: flex-end;
        }

        .msg-wrap.bot {
            align-self: flex-start;
        }

        .msg-sender {
            font-size: 0.68rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.3rem;
            padding: 0 0.25rem;
        }

        .msg {
            padding: 0.85rem 1.15rem;
            border-radius: 16px;
            font-size: 0.88rem;
            line-height: 1.6;
        }

        .user .msg {
            background: #0F172A;
            color: #FFFFFF;
            border-bottom-right-radius: 4px;
        }

        .bot .msg {
            background: #FFFFFF;
            border: 1px solid var(--border);
            color: #1E293B;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        .msg table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.75rem 0;
            font-size: 0.8rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }

        .msg th, .msg td {
            padding: 0.5rem 0.75rem;
            border-bottom: 1px solid #F1F5F9;
            text-align: left;
        }

        .msg th {
            background: #F8FAFC;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
        }

        .input-dock {
            display: flex;
            gap: 0.5rem;
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.5rem 0.75rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        .input-dock:focus-within {
            border-color: var(--accent-black);
        }

        .chat-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-size: 0.88rem;
            font-family: inherit;
            padding: 0.4rem 0.5rem;
        }

        .btn-send {
            background: #0F172A;
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            padding: 0.4rem 1.25rem;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: opacity 0.15s;
        }

        .btn-send:hover {
            opacity: 0.9;
        }

        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="crest-icon">AU</div>
            <div>
                <h1>Apex University</h1>
                <span>Campus Copilot</span>
            </div>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            <span>ERP v4.1 • RAG Online</span>
        </div>
    </header>

    <div class="container">
        <!-- Login Card -->
        <div id="login-section">
            <h2 class="login-title">Student Portal</h2>
            <p class="login-subtitle">Sign in to your official academic workspace</p>
            
            <div id="error"></div>

            <div class="presets-label">
                <span>Select Test Student</span>
                <span>Auto-populates</span>
            </div>

            <div class="presets-grid">
                <button class="preset-btn active" onclick="setPreset('demo_student_1', this)">
                    <span class="preset-name">Liam Sterling</span>
                    <span class="preset-role">CSE • Sem 2</span>
                </button>
                <button class="preset-btn" onclick="setPreset('demo_student_2', this)">
                    <span class="preset-name">Maya Chen</span>
                    <span class="preset-role">EE • Sem 2</span>
                </button>
                <button class="preset-btn" onclick="setPreset('demo_student_3', this)">
                    <span class="preset-name">Jordan Vance</span>
                    <span class="preset-role">ME • Sem 1</span>
                </button>
            </div>

            <div class="form-group">
                <label class="form-label">Enrollment ID</label>
                <input type="text" id="username" class="input-field" placeholder="e.g. demo_student_1" value="demo_student_1">
            </div>

            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" id="password" class="input-field" placeholder="Password" value="demopass">
            </div>

            <button onclick="login()" class="btn-primary">Sign In to Academic Workspace</button>
        </div>

        <!-- Chat Workspace -->
        <div id="chat-section" class="hidden">
            <div class="chat-header">
                <div class="student-pill">
                    <div class="student-avatar" id="student-initials">S</div>
                    <div>
                        <div class="student-info" id="student-name">Verified Student</div>
                        <div class="student-sub" id="student-enrollment">Enrolled in 2nd Semester</div>
                    </div>
                </div>
                <button onclick="logout()" class="btn-logout">Sign Out</button>
            </div>

            <div class="prompt-pills">
                <button class="pill-btn" onclick="quickQuery('What is my attendance percentage across all courses?')">Check Attendance</button>
                <button class="pill-btn" onclick="quickQuery('What are my pending fee dues and when is the deadline?')">Fee Details</button>
                <button class="pill-btn" onclick="quickQuery('What is my course schedule and timetable for today?')">Today's Timetable</button>
                <button class="pill-btn" onclick="quickQuery('What are the rules and penalties if attendance falls below 75%?')">University Regulations</button>
            </div>

            <div id="chat"></div>

            <div class="input-dock">
                <input type="text" id="message" class="chat-input" placeholder="Ask about attendance, fees, classes, exams, or campus policies..." onkeypress="if(event.key === 'Enter') send()">
                <button onclick="send()" class="btn-send">Send</button>
            </div>
        </div>
    </div>

    <script>
        let token = localStorage.getItem("token");
        let currentRunId = null;
        let currentQuery = "";
        let currentResponse = "";

        if (token) {
            initChat();
        }

        function setPreset(username, el) {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            document.getElementById('username').value = username;
            document.getElementById('password').value = 'demopass';
        }

        async function initChat() {
            document.getElementById('login-section').classList.add('hidden');
            document.getElementById('chat-section').classList.remove('hidden');
            try {
                const res = await fetch('/me/', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.name) {
                        document.getElementById('student-name').innerText = data.name;
                        document.getElementById('student-enrollment').innerText = `${data.enrollment_no} • ${data.department || 'Student'}`;
                        document.getElementById('student-initials').innerText = data.name[0] || 'S';
                    }
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function login() {
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const errDiv = document.getElementById('error');
            try {
                const res = await fetch('/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: `username=${encodeURIComponent(u)}&password=${encodeURIComponent(p)}`
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || "Authentication failed. Check credentials.");
                }
                const data = await res.json();
                token = data.access_token;
                localStorage.setItem("token", token);
                errDiv.style.display = "none";
                initChat();
            } catch (e) {
                errDiv.innerText = e.message;
                errDiv.style.display = "block";
            }
        }

        function logout() {
            localStorage.removeItem("token");
            token = null;
            document.getElementById('login-section').classList.remove('hidden');
            document.getElementById('chat-section').classList.add('hidden');
        }

        function appendMsg(text, type) {
            const wrap = document.createElement('div');
            wrap.className = `msg-wrap ${type}`;
            
            const sender = document.createElement('div');
            sender.className = 'msg-sender';
            sender.innerText = type === 'user' ? 'Student' : 'Apex Academic Copilot';
            wrap.appendChild(sender);

            const div = document.createElement('div');
            div.className = 'msg';
            div.innerHTML = text;
            wrap.appendChild(div);

            document.getElementById('chat').appendChild(wrap);
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
            return div;
        }

        function quickQuery(queryText) {
            document.getElementById('message').value = queryText;
            send();
        }

        async function send() {
            if (!token) return;
            const input = document.getElementById('message');
            const msg = input.value.trim();
            if (!msg) return;
            input.value = "";

            appendMsg(msg, 'user');
            currentQuery = msg;
            currentResponse = "";
            currentRunId = null;

            const botDiv = appendMsg("Retrieving records from campus database...", 'bot');

            try {
                const res = await fetch('/chat/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ message: msg })
                });

                if (!res.ok) {
                    if (res.status === 429) throw new Error("Rate limit exceeded. Please wait a moment.");
                    throw new Error("Chat request failed.");
                }

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                botDiv.innerHTML = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const events = chunk.split('\\n\\n').filter(x => x.startsWith('event:'));

                    for (const eventStr of events) {
                        const lines = eventStr.split('\\n');
                        const ev = lines[0].replace('event: ', '');
                        const data = JSON.parse(lines[1].replace('data: ', ''));

                        if (ev === 'run_id') {
                            currentRunId = data.run_id;
                        } else if (ev === 'token') {
                            currentResponse += data.token;
                            botDiv.innerHTML = formatMarkdown(currentResponse);
                        } else if (ev === 'done') {
                            currentResponse = data.final_answer;
                            botDiv.innerHTML = formatMarkdown(currentResponse);
                        } else if (ev === 'error') {
                            botDiv.innerHTML = `<span style="color: #DC2626;">Error: ${data.error}</span>`;
                        }
                    }
                    document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
                }
            } catch (e) {
                botDiv.innerHTML = `<span style="color: #DC2626;">${e.message}</span>`;
            }
        }

        function formatMarkdown(text) {
            return text
                .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/^\\* (.*$)/gim, '• $1')
                .replace(/\\n/g, '<br>');
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
