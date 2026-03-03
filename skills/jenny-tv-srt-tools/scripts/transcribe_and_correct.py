#!/usr/bin/env python3
"""Transcribe media and AI-correct subtitles through FunClip Gradio APIs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

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


def _as_dict(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} returned {type(value).__name__}, expected dict.")
    return value


def _predict_with_retry(
    client: Client,
    *args: Any,
    api_name: str,
    max_retries: int,
    retry_backoff: float,
    operation_name: str,
) -> Any:
    attempts = max(1, max_retries + 1)
    delay_base = max(0.0, retry_backoff)
    for attempt in range(1, attempts + 1):
        try:
            return client.predict(*args, api_name=api_name)
        except Exception as exc:
            if attempt >= attempts:
                raise RuntimeError(
                    f"{operation_name} failed after {attempts} attempt(s): {exc}"
                ) from exc
            sleep_s = delay_base * (2 ** (attempt - 1))
            print(
                f"{operation_name} attempt {attempt}/{attempts} failed: {exc}. "
                f"Retrying in {sleep_s:.1f}s...",
                file=sys.stderr,
            )
            time.sleep(sleep_s)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a media file and AI-correct the generated SRT."
    )
    parser.add_argument("input_media", help="Input media file path (.mp3/.wav/.m4a/.mp4/...)")
    parser.add_argument("output_srt", help="Output SRT path")
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
    parser.add_argument(
        "--return-traditional",
        action="store_true",
        help="Set return_traditional=True for /srt_correct.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=600.0,
        help="HTTP request timeout (seconds) for each API call.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retry count for transient API errors (total attempts = max_retries + 1).",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=2.0,
        help="Initial backoff seconds for retries (exponential).",
    )
    parser.add_argument(
        "--save-raw-on-correction-failure",
        action="store_true",
        help="Write transcribed SRT if correction fails instead of exiting with error.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_media = Path(args.input_media).expanduser().resolve()
    output_srt = Path(args.output_srt).expanduser().resolve()
    if not input_media.exists():
        print(f"Input media file not found: {input_media}", file=sys.stderr)
        return 2

    token = _resolve_cf_access_token(args.api_url, args.cf_access_token)
    httpx_kwargs: Dict[str, Any] = {}
    if args.request_timeout and args.request_timeout > 0:
        httpx_kwargs["timeout"] = args.request_timeout
    client = Client(
        args.api_url,
        headers={"CF-Access-Token": token},
        httpx_kwargs=httpx_kwargs or None,
    )

    transcribe_res = _predict_with_retry(
        client,
        handle_file(str(input_media)),
        api_name="/transcribe",
        max_retries=args.max_retries,
        retry_backoff=args.retry_backoff,
        operation_name="/transcribe",
    )
    transcribe_res = _as_dict(transcribe_res, "/transcribe")
    print("transcribe status:", transcribe_res.get("status", ""))

    srt_text = transcribe_res.get("srt_content", "")
    if not isinstance(srt_text, str) or not srt_text.strip():
        raise RuntimeError("/transcribe returned empty srt_content.")

    try:
        correct_res = _predict_with_retry(
            client,
            srt_text,
            args.api_key,
            args.model_name,
            args.custom_model,
            args.base_url,
            bool(args.return_traditional),
            api_name="/srt_correct",
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            operation_name="/srt_correct",
        )
    except Exception:
        if not args.save_raw_on_correction_failure:
            raise

        output_srt.parent.mkdir(parents=True, exist_ok=True)
        output_srt.write_text(srt_text, encoding="utf-8")
        print(
            "warning: /srt_correct failed; wrote raw transcription SRT because "
            "--save-raw-on-correction-failure is enabled.",
            file=sys.stderr,
        )
        print(f"wrote: {output_srt}")
        return 0

    correct_res = _as_dict(correct_res, "/srt_correct")
    print("correct status:", correct_res.get("status", ""))

    corrected_srt = correct_res.get("corrected_srt")
    final_srt = corrected_srt if isinstance(corrected_srt, str) and corrected_srt.strip() else srt_text

    output_srt.parent.mkdir(parents=True, exist_ok=True)
    output_srt.write_text(final_srt, encoding="utf-8")
    print(f"wrote: {output_srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
