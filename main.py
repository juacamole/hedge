import requests

LLAMA_IP = "127.0.0.1"
LLAMA_PORT = "8080"
URI = "/completion"
MODEL = "qwen3.8-27b-abliterated"
PROMPT = "The capital of France is"
N_PREDICT = 1
N_PROBS = 1
TEMP = 1

url = "http://" + LLAMA_IP + ":" + LLAMA_PORT + URI

settings = {
    "model": MODEL,
    "prompt": PROMPT,
    "n_predict": N_PREDICT,
    "n_probs": N_PROBS,
    "temperature": TEMP,
    "post_sampling_probs": False,
}

result = requests.post(url, json=settings)
print(result.json())
