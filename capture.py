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


def convert(response) -> list[dict]:
    entries = response["completion_probabilities"]
    records = []
    for pos, entry in enumerate(entries):
        chosen_token = entry["token"]
        chosen_prob = math.exp(entry["logprob"])

        alternatives = []
        for alt in entry["top_logprobs"]:
            alternatives.append(
                {"token": alt["token"], "prob": math.exp(alt["logprob"])}
            )

        record = {
            "pos": pos,
            "token": chosen_token,
            "prob": chosen_prob,
            "top_probs": alternatives,
        }
        records.append(record)
    return records


def run(settings: dict) -> dict:
    sent = build_settings(settings)
    result = requests.post(build_url(), json=sent, timeout=300)
    result.raise_for_status()
    return {"meta": sent, "records": convert(result.json())}


if __name__ == "__main__":
    print("please run main.py instead")
