---
name: jenny-tv-srt-tools
description: Call FunClip Gradio API endpoints from automation scripts with gradio_client. Use when Codex/Claude or other tools need to interact with deployed FunClip service (https://srt.xcv58.xyz/) for media transcription, SRT AI auto-correction, Traditional Chinese conversion, or English translation.
---

# FunClip Gradio API Client

## Overview
Call FunClip features through stable Gradio API endpoints with `gradio_client`.
Use this skill for machine-to-machine access instead of manual UI clicking.

## Workflow

1. Create and activate a virtual environment in the caller workspace.
2. Install `gradio_client` inside that environment.
3. Run `cloudflared access login https://srt.xcv58.xyz/` once on the machine.
4. Resolve a token with `cloudflared access token -app https://srt.xcv58.xyz/`.
5. Create a client with auth headers:
   `Client("https://srt.xcv58.xyz/", headers={"CF-Access-Token": token})`.
6. Run `client.view_api(all_endpoints=True)` to confirm endpoint names and input shapes.
7. Call the endpoint by `api_name`.
8. For file inputs, always wrap paths with `handle_file(...)`.
9. For long-running jobs, prefer async endpoints (`/submit_transcribe_and_correct`, `/submit_srt_correct`) and poll with `/async_job_status`.

## Recommended Workflows

### 1) Audio/Video -> SRT -> AI Correction

1. Call `/transcribe` with one media file (`.mp3`, `.wav`, `.m4a`, `.mp4`, etc.).
2. Read `srt_content` from the response.
3. Call `/srt_correct` with that `srt_content`.
4. Use `corrected_srt` for downstream steps (fallback to original `srt_content` if empty).
5. Prefer `scripts/transcribe_and_correct.py` for deterministic automation.

### 2) Chinese SRT -> Traditional Chinese SRT -> AI Correction

1. Call `/srt_translate_traditional_text` with one or more `.srt` files.
2. Read translated SRT text from the JSON response.
3. For final cleanup, call `/srt_correct` on the translated SRT content.
4. Prefer this flow when you want fast Traditional conversion first, then quality polish.
5. Prefer `scripts/to_traditional_and_correct.py` for deterministic automation.

## Endpoints

- `/transcribe`
Purpose: Transcribe one audio/video file and return markdown text + SRT.
Input: one media file.

- `/srt_correct`
Purpose: AI-correct SRT content text and optionally return a Traditional artifact path.
Inputs: `srt_content`, `api_key`, `model_name`, `custom_model`, `base_url`, `return_traditional`.

- `/srt_translate_traditional`
Purpose: Convert uploaded SRT file(s) to Traditional Chinese.
Input: one or more `.srt` files.

- `/srt_translate_traditional_text`
Purpose: Convert uploaded SRT file(s) to Traditional Chinese and return translated text JSON.
Input: one or more `.srt` files.

- `/srt_translate_english`
Purpose: Translate uploaded SRT file(s) to English via LLM.
Inputs: one or more `.srt` files plus LLM settings.

- `/submit_transcribe_and_correct`
Purpose: Submit async transcribe + correction job for long-running requests.
Inputs: media file + correction settings.

- `/submit_srt_correct`
Purpose: Submit async correction-only job for long-running requests.
Inputs: SRT text + correction settings.

- `/async_job_status`
Purpose: Poll async job status (`queued/running/completed/failed`) and optionally fetch result.
Inputs: `job_id`, `include_result`.

## Input Rules

- Use a Cloudflare Access token (`CF-Access-Token`) when creating the client.
- Use absolute file paths for `handle_file(...)`.
- Pass file lists for endpoints expecting `file_count="multiple"` even when sending one file.
- Set `model_name="Custom"` only when `custom_model` is provided.
- Pass empty string for `api_key` only if server-side `OPENAI_API_KEY` is configured.

## Output Handling

- Read `status` fields first.
- Prefer dict JSON outputs (`translated_srt`, `items`) for Traditional text workflows.
- Use returned SRT text for downstream workflows when available.
- `corrected_traditional_file_path` may be server-local and not directly readable from the caller.
- Treat returned download paths as Gradio-served artifacts, not guaranteed local filesystem paths.

## Error Handling

- `ValueError: Could not fetch config`: usually missing Cloudflare Access auth; login and pass token header.
- `HTTP 302` redirect to `cloudflareaccess.com`: request is unauthenticated; provide `CF-Access-Token`.
- `externally-managed-environment` from `pip`: create a venv and install dependencies there.
- Missing keys like `srt_content` or `translated_srt`: inspect response shape and prefer `/srt_translate_traditional_text` JSON output.
- For long-running calls, use async submit + polling to avoid opaque blocking waits.
- On quota/rate-limit errors, retry with another key/model or back off.
- On schema mismatch, rerun `view_api(all_endpoints=True)` and align argument order.

## References

- For full copy-paste examples, read [`references/gradio_client_examples.md`](references/gradio_client_examples.md).
- Reusable scripts:
  - [`scripts/transcribe_and_correct.py`](scripts/transcribe_and_correct.py)
  - [`scripts/to_traditional_and_correct.py`](scripts/to_traditional_and_correct.py)
