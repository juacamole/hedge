import math

import requests

IP = "127.0.0.1"
PORT = "8080"
PATH = "/completion"


def build_url() -> str:
    return "http://" + IP + ":" + PORT + PATH


def build_settings(settings: dict) -> dict:
    return {
        "model": settings["model"],
        "prompt": settings["prompt"],
        "n_predict": settings["n_predict"],
        "n_probs": settings["n_probs"],
        "temperature": settings["temperature"],
        "post_sampling_probs": False,
        "seed": settings["seed"],
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


def run(settings: dict):
    result = requests.post(build_url(), json=build_settings(settings), timeout=300)
    return {"meta": settings, "records": convert(result)}


if __name__ == "__main__":
    print("please run main.py instead")
