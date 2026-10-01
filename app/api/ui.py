from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

@router.get("/")
async def get_ui():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>University Assistant</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            #chat { height: 400px; border: 1px solid #ccc; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
            .msg { margin-bottom: 10px; padding: 10px; border-radius: 5px; }
            .user { background: #e3f2fd; text-align: right; }
            .bot { background: #f5f5f5; }
            .hidden { display: none; }
            .feedback-btn { cursor: pointer; margin-left: 5px; font-size: 12px; }
            #error { color: red; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>University Assistant</h1>
        <div id="error"></div>
        
        <div id="login-section">
            <h2>Login</h2>
            <input type="text" id="username" placeholder="Enrollment No (e.g. demo_student_1)" value="demo_student_1">
            <input type="password" id="password" placeholder="Password" value="demopass">
            <button onclick="login()">Login</button>
        </div>
        
        <div id="chat-section" class="hidden">
            <button onclick="logout()" style="float: right;">Logout</button>
            <h2>Chat</h2>
            <div id="chat"></div>
            <div style="display: flex;">
                <input type="text" id="message" placeholder="Ask a question..." style="flex-grow: 1; padding: 5px;" onkeypress="if(event.key === 'Enter') send()">
                <button onclick="send()">Send</button>
            </div>
        </div>

        <script>
            let token = localStorage.getItem("token");
            let currentRunId = null;
            let currentQuery = "";
            let currentResponse = "";
            
            if(token) {
                document.getElementById('login-section').classList.add('hidden');
                document.getElementById('chat-section').classList.remove('hidden');
            }

            async function login() {
                const u = document.getElementById('username').value;
                const p = document.getElementById('password').value;
                try {
                    const res = await fetch('/auth/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: `username=${encodeURIComponent(u)}&password=${encodeURIComponent(p)}`
                    });
                    if(!res.ok) throw new Error("Login failed");
                    const data = await res.json();
                    token = data.access_token;
                    localStorage.setItem("token", token);
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('chat-section').classList.remove('hidden');
                    document.getElementById('error').innerText = "";
                } catch(e) {
                    document.getElementById('error').innerText = e.message;
                }
            }

            function logout() {
                localStorage.removeItem("token");
                token = null;
                document.getElementById('login-section').classList.remove('hidden');
                document.getElementById('chat-section').classList.add('hidden');
            }

            function appendMsg(text, type) {
                const div = document.createElement('div');
                div.className = `msg ${type}`;
                div.innerHTML = text;
                document.getElementById('chat').appendChild(div);
                document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
                return div;
            }

            async function send() {
                if(!token) return;
                const input = document.getElementById('message');
                const msg = input.value;
                if(!msg) return;
                input.value = "";
                
                appendMsg(msg, 'user');
                currentQuery = msg;
                currentResponse = "";
                currentRunId = null;
                
                const botDiv = appendMsg("...", 'bot');
                
                try {
                    const res = await fetch('/chat/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({message: msg})
                    });
                    
                    if(!res.ok) {
                        if(res.status === 429) throw new Error("Rate limit exceeded");
                        throw new Error("Chat failed");
                    }
                    
                    const reader = res.body.getReader();
                    const decoder = new TextDecoder();
                    botDiv.innerHTML = "";
                    
                    while(true) {
                        const {done, value} = await reader.read();
                        if(done) break;
                        const chunk = decoder.decode(value);
                        const events = chunk.split('\n\n').filter(x => x.startsWith('event:'));
                        
                        for(const eventStr of events) {
                            const lines = eventStr.split('\n');
                            const ev = lines[0].replace('event: ', '');
                            const data = JSON.parse(lines[1].replace('data: ', ''));
                            
                            if(ev === 'run_id') {
                                currentRunId = data.run_id;
                            } else if (ev === 'token') {
                                currentResponse += data.token;
                                botDiv.innerHTML = currentResponse;
                            } else if (ev === 'done') {
                                currentResponse = data.final_answer;
                                botDiv.innerHTML = currentResponse + ` 
                                    <button class="feedback-btn" onclick="feedback(1, this)">👍</button>
                                    <button class="feedback-btn" onclick="feedback(0, this)">👎</button>
                                `;
                            } else if (ev === 'error') {
                                botDiv.innerHTML = `Error: ${data.error}`;
                            }
                        }
                    }
                } catch(e) {
                    botDiv.innerHTML = e.message;
                }
            }
            
            async function feedback(score, btn) {
                if(!currentRunId) return;
                try {
                    await fetch('/chat/feedback', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            run_id: currentRunId,
                            score: score,
                            query: currentQuery,
                            response: currentResponse
                        })
                    });
                    btn.parentElement.querySelectorAll('.feedback-btn').forEach(b => b.remove());
                } catch(e) {
                    console.error("Feedback failed", e);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
