import requests
import json

BASE = "http://127.0.0.1:8000"

print("--- 1. Testing GET /health ---")
r = requests.get(f"{BASE}/health")
print("Status:", r.status_code)
print("Payload:", json.dumps(r.json(), indent=2))
assert r.status_code == 200

print("\n--- 2. Testing GET /api/documents ---")
r = requests.get(f"{BASE}/api/documents")
print("Status:", r.status_code)
docs = r.json()
print(f"Total documents: {len(docs['documents'])} | Total chunks: {docs['total_chunks']}")
assert r.status_code == 200

print("\n--- 3. Testing POST /api/ask ---")
payload = {
    "question": "What is FloCard and how does it integrate with CRM?",
    "top_k": 3
}
r = requests.post(f"{BASE}/api/ask", json=payload)
print("Status:", r.status_code)
ask_data = r.json()
print("Question:", ask_data["question"])
print("Answer:", ask_data["answer"])
print("Latency:", ask_data["latency_ms"], "ms")
print("Citations count:", len(ask_data["citations"]))
assert r.status_code == 200
assert len(ask_data["citations"]) > 0

print("\n--- 4. Testing POST /api/export/docx ---")
r = requests.post(f"{BASE}/api/export/docx", json=ask_data)
print("Status:", r.status_code)
print("Content-Type:", r.headers.get("content-type"))
print("File size bytes:", len(r.content))
assert r.status_code == 200
assert len(r.content) > 1000

print("\n--- 5. Testing POST /api/export/xlsx ---")
r = requests.post(f"{BASE}/api/export/xlsx", json=ask_data)
print("Status:", r.status_code)
print("Content-Type:", r.headers.get("content-type"))
print("File size bytes:", len(r.content))
assert r.status_code == 200
assert len(r.content) > 1000

print("\n--- 6. Testing GET /api/metrics ---")
r = requests.get(f"{BASE}/api/metrics")
print("Status:", r.status_code)
print("Payload:", json.dumps(r.json(), indent=2))
assert r.status_code == 200

print("\n--- 7. Testing GET / (Web Dashboard) ---")
r = requests.get(f"{BASE}/")
print("Status:", r.status_code)
print("HTML Title Found:", "<title>AI Knowledge Assistant" in r.text)
assert r.status_code == 200

print("\n>>> ALL API AND EXPORT ENDPOINTS FUNCTIONING 100% PERFECTLY! <<<")
