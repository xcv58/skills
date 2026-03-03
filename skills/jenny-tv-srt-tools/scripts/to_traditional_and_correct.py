#!/usr/bin/env python3
"""Convert SRT to Traditional Chinese, then AI-correct through FunClip APIs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from gradio_client import Client, handle_file


def _resolve_cf_access_token(api_url: str, explicit_token: str) -> str:
    if explicit_token:
        return explicit_token
    env_token = os.getenv("CF_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token

    try:
        token = subprocess.check_output(
            ["cloudflared", "access", "token", "-app", api_url],
            text=True,
        ).strip()
    except FileNotFoundError as exc:
        raise RuntimeError(
            "cloudflared is not installed. Install cloudflared or pass --cf-access-token."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Could not read Cloudflare Access token. Run "
            f"`cloudflared access login {api_url}` first, or pass --cf-access-token."
        ) from exc

    if not token:
        raise RuntimeError("Cloudflare Access token is empty.")
    return token


def _extract_translated(result: Any) -> Tuple[str, str]:
    if isinstance(result, (list, tuple)):
        translated = result[1] if len(result) > 1 else ""
        status = result[3] if len(result) > 3 else ""
        if isinstance(translated, str):
            return translated, str(status)
        return "", str(status)

    if isinstance(result, dict):
        status = str(result.get("status", ""))
        for key in ("translated_srt", "srt_content", "output_srt", "text"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value, status
        return "", status

    return "", ""


def _as_dict(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} returned {type(value).__name__}, expected dict.")
    return value


def _pick_corrected_srt(result: Dict[str, Any]) -> str:
    candidates: Iterable[str] = (
        "corrected_srt_traditional",
        "corrected_traditional_srt",
        "traditional_srt",
        "corrected_srt",
    )
    for key in candidates:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an SRT to Traditional Chinese and run AI correction."
    )
    parser.add_argument("input_srt", help="Input SRT path")
    parser.add_argument("output_srt", help="Output Traditional+corrected SRT path")
    parser.add_argument("--api-url", default="https://srt.xcv58.xyz/", help="FunClip URL")
    parser.add_argument("--api-key", default="", help="LLM API key (empty uses server-side key)")
    parser.add_argument("--model-name", default="gpt-4o-mini", help="Model name")
    parser.add_argument("--custom-model", default="", help="Custom model name when model is Custom")
    parser.add_argument("--base-url", default="", help="LLM base URL")
    parser.add_argument(
        "--cf-access-token",
        default="",
        help="Cloudflare Access token. If omitted, use CF_ACCESS_TOKEN env or cloudflared.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_srt = Path(args.input_srt).expanduser().resolve()
    output_srt = Path(args.output_srt).expanduser().resolve()
    if not input_srt.exists():
        print(f"Input SRT file not found: {input_srt}", file=sys.stderr)
        return 2

    token = _resolve_cf_access_token(args.api_url, args.cf_access_token)
    client = Client(args.api_url, headers={"CF-Access-Token": token})

    trad_res = client.predict(
        [handle_file(str(input_srt))],
        api_name="/safe_translate_traditional_wrapper",
    )
    translated_srt, translate_status = _extract_translated(trad_res)
    print("traditional status:", translate_status)
    if not translated_srt.strip():
        raise RuntimeError("Traditional translation returned empty text.")

    correct_res = client.predict(
        translated_srt,
        args.api_key,
        args.model_name,
        args.custom_model,
        args.base_url,
        True,
        api_name="/srt_correct",
    )
    correct_res = _as_dict(correct_res, "/srt_correct")
    print("correct status:", correct_res.get("status", ""))

    final_srt = _pick_corrected_srt(correct_res) or translated_srt

    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_srt.write_text(final_srt, encoding="utf-8")
    print(f"wrote: {output_srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
