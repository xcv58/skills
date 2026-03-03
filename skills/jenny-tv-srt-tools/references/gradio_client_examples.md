# Gradio Client Examples

Target URL:
- `https://srt.xcv58.xyz/`

Install in a virtual environment:
```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip gradio_client
```

Authenticate Cloudflare Access (required by this host):
```shell
cloudflared access login https://srt.xcv58.xyz/
```

Build a client:
```python
import os
import subprocess

from gradio_client import Client

api_url = "https://srt.xcv58.xyz/"
token = os.getenv("CF_ACCESS_TOKEN") or subprocess.check_output(
    ["cloudflared", "access", "token", "-app", api_url],
    text=True,
).strip()
client = Client(api_url, headers={"CF-Access-Token": token})
```

Inspect endpoints:
```python
print(client.view_api(all_endpoints=True))
```

Audio/video -> SRT -> AI correction:
```python
from gradio_client import handle_file

media_path = "/absolute/path/input.mp4"
# 1) Transcribe audio/video -> text + srt
transcribe_res = client.predict(
    handle_file(media_path),
    api_name="/transcribe",
)
print("transcribe status:", transcribe_res.get("status"))
srt_text = transcribe_res.get("srt_content", "")

# 2) AI auto-correct SRT text
correct_res = client.predict(
    srt_text,         # srt_content
    "sk-xxx",         # api_key (or "" to use server-side OPENAI_API_KEY)
    "gpt-4o-mini",    # model_name
    "",               # custom_model (used only when model_name == "Custom")
    "",               # base_url
    True,             # return_traditional
    api_name="/srt_correct",
)
print("correct status:", correct_res.get("status"))
final_srt = correct_res.get("corrected_srt") or srt_text
```

Chinese SRT -> Traditional -> AI correction:
```python
# 3) Translate to Traditional text (JSON endpoint)
trad_res = client.predict(
    [handle_file("/absolute/path/a.srt")],
    api_name="/srt_translate_traditional_text",
)
status = trad_res.get("status", "")
translated_srt = trad_res.get("translated_srt", "")
if not translated_srt and trad_res.get("items"):
    translated_srt = trad_res["items"][0].get("translated_srt", "")
print("traditional status:", status)

# 4) AI correction on translated text
correct_res = client.predict(
    translated_srt,  # srt_content
    "",              # api_key
    "gpt-4o-mini",   # model_name
    "",              # custom_model
    "",              # base_url
    True,            # return_traditional
    api_name="/srt_correct",
)
print("correct status:", correct_res.get("status"))
final_srt = correct_res.get("corrected_srt") or translated_srt
```

Async submit + poll (long-running):
```python
# Submit a long job
submit_res = client.predict(
    handle_file("/absolute/path/input.mp3"),
    "",              # api_key
    "gpt-4o-mini",   # model_name
    "",              # custom_model
    "",              # base_url
    True,            # return_traditional
    api_name="/submit_transcribe_and_correct",
)
job_id = submit_res["job_id"]

# Poll until completed/failed
while True:
    status_res = client.predict(job_id, True, api_name="/async_job_status")
    print(status_res["status"], status_res.get("stage"), status_res.get("eta_seconds"))
    if status_res["status"] in {"completed", "failed"}:
        break
```

Notes:
- `/srt_translate_traditional` may return preview/download metadata rather than direct translated text.
- `corrected_traditional_file_path` may point to a server-local path and not be directly readable.

Run reusable scripts:
```shell
python scripts/transcribe_and_correct.py /abs/in.mp3 /abs/out.srt --request-timeout 600 --max-retries 2
python scripts/to_traditional_and_correct.py /abs/in.srt /abs/out_traditional.srt --request-timeout 600 --max-retries 2
```
