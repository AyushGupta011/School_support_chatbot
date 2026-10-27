from locust import HttpUser, task, between
import json

class ChatUser(HttpUser):
    wait_time = between(1, 2)
    
    def on_start(self):
        # Authenticate first
        res = self.client.post("/auth/login", data={"username": "demo_student_1", "password": "demopass"})
        if res.status_code == 200:
            self.token = res.json().get("access_token")
        else:
            self.token = ""

    @task
    def ask_question(self):
        if not self.token: return
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        # For load test, hit cache by repeatedly asking same question
        payload = {"message": "What is the fee structure?"}
        
        with self.client.post("/chat/", headers=headers, json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.success() # Rate limited, but endpoint behaved correctly
            else:
                response.failure(f"Got {response.status_code}")
