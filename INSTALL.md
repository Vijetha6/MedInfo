Local summarizer (optional) — install instructions

If you want the local t5-small summarizer to work in this project (recommended for on-device summaries), you need the `transformers` and `torch` Python packages installed in your environment.

PowerShell / pip (recommended for Windows):

1. Activate your virtual environment (if using one) — replace `.\.venv\Scripts\Activate` with your venv path if different:

   powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { .\.venv\Scripts\Activate; python -m pip install --upgrade pip }"

2. Install dependencies:

   powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { pip install transformers torch --upgrade }"

Notes / alternatives:

- If you have a GPU and want better performance, install the appropriate `torch` build for your CUDA version (see https://pytorch.org/get-started/locally/).
- On some Windows setups, `torch` may be large; consider using a small CPU-only wheel or running the app on a machine with enough memory. If `torch` fails to install, the application will fall back to the built-in rule-based summarizer.

After installing, restart the Flask server and the app will try to load the local summarizer automatically on first call (or immediately if preloading is enabled).