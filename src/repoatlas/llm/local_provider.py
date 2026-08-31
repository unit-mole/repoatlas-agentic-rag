import httpx


class LocalCoderProvider:
    def __init__(self, base_url="http://localhost:8000/v1", model="Qwen/Qwen3-8B", timeout=180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system, user, temperature=0.2, max_tokens=2048):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = httpx.post(self.base_url + "/chat/completions", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
