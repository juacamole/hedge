import math

import requests

LLAMA_IP = "127.0.0.1"
LLAMA_PORT = "8080"
PATH = "/completion"
MODEL = "qwen3.8-27b-abliterated"
PROMPT = "The capital of France is"
N_PREDICT = 3
N_PROBS = 3
TEMP = 1
SEED = 0


def build_url() -> str:
    return "http://" + LLAMA_IP + ":" + LLAMA_PORT + PATH


def build_settings() -> dict:
    return {
        "model": MODEL,
        "prompt": PROMPT,
        "n_predict": N_PREDICT,
        "n_probs": N_PROBS,
        "temperature": TEMP,
        "post_sampling_probs": False,
        "seed": SEED,
    }


def convert(response):
    entries = response["completion_probabilities"]
    records = []
    for pos, entry in enumerate(entries):
        chosen_token = entry["token"]
        chosen_p = math.exp(entry["logprob"])

        alternatives = []
        for alt in entry["top_logprobs"]:
            alternatives.append({"token": alt["token"], "p": math.exp(alt["logprob"])})

        record = {
            "pos": pos,
            "token": chosen_token,
            "prob": chosen_p,
            "top_logprobs": alternatives,
        }
        records.append(record)
    return records


result = requests.post(build_url(), json=build_settings(), timeout=300)
print(convert(result.json()))
