## Strategic Analysis Endpoint — Diagnosis & Fix

Summary
-------
I attempted to reproduce a failing call to the strategic analysis endpoint (`POST /api/v1/resumes/strategic-analysis`). The server could not be started locally due to a Python SSL import failure, so I could not make an HTTP request to the endpoint. Below are the exact error, root causes, reproduction steps, fixes, and recommended next steps to fully verify and stabilise the endpoint.

What I ran
-----------
- Started the FastAPI server with: `uvicorn main:app --reload --port 8000` (from project root)
- Observed immediate crash during Python startup:

```
ImportError: dlopen(.../_ssl.cpython-310-darwin.so): Library not loaded: /opt/homebrew/opt/openssl@1.1/lib/libssl.1.1.dylib
  Reason: tried: '/opt/homebrew/opt/openssl@1.1/lib/libssl.1.1.dylib' (no such file)
```

Root cause
----------
1. Python's _ssl extension module (part of CPython) dynamically links to OpenSSL libraries (libssl). The running Python interpreter (managed by `pyenv` in this environment) was built to link against `openssl@1.1` in Homebrew's prefix (`/opt/homebrew/opt/openssl@1.1`) but that library is missing on the machine.
2. This usually happens when:
   - Homebrew removed or upgraded `openssl@1.1` (for example, to `openssl@3`) after Python was installed; or
   - Python was compiled against a Homebrew OpenSSL instance that was later removed.

Why this blocks your endpoint test
---------------------------------
- The `uvicorn` command imports Python's `ssl` module at startup. Because `_ssl` fails to import, the process aborts before FastAPI and the `/strategic-analysis` route are available, so no HTTP request can be made.

Immediate remediation options (macOS, zsh)
----------------------------------------
Choose one of the following based on preference and permissions.

Option A — Install the missing OpenSSL 1.1 library (fastest fix):

```bash
# Install openssl@1.1 via Homebrew
brew install openssl@1.1

# (Optional) Verify the file exists
ls -l /opt/homebrew/opt/openssl@1.1/lib/libssl*.dylib
```

After installing, re-run the server. If Python still can't find the library, you may need to reinstall or rebuild the pyenv Python so the binary links correctly (see Option B).

Option B — Reinstall Python under pyenv pointing to the Homebrew OpenSSL (recommended for reproducible dev env):

```bash
# Ensure openssl is present
brew install openssl@1.1

# Export flags so pyenv build picks up the Homebrew OpenSSL
export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/openssl@1.1/lib/pkgconfig"

# Reinstall the Python version (example uses 3.10.8—use the project's version)
pyenv uninstall -f 3.10.8
pyenv install 3.10.8
pyenv local 3.10.8

# Reinstall project deps (poetry or pip as appropriate)
poetry install --no-interaction
```

Option C — Use system Python or Docker as a short-term workaround:

```bash
# Run server with system python (if it has ssl support)
/usr/bin/python3 -m uvicorn main:app --port 8000

# Or: run the app via Docker to avoid local pyenv/openssl issues
# (Add a Dockerfile and run in container where Python is built with openssl)
```

Other observations and potential follow-ups
-----------------------------------------
- Endpoint signature and client expectations
  - The endpoint expects multipart/form-data (Form fields for `resume_id`, `job_description_url`, `design_prompt` plus an optional `inspiration_image` UploadFile). The test script `test_strategic_endpoint.py` uses `requests.post(..., data=form_data, files=files)` which is correct.
  - There is an existing doc `app/docs/STRATEGIC_API_MULTIPART_FIX.md` addressing multipart/422 errors — consult that if you later observe 422s or OpenAPI form UI problems.

- Timeouts and agent behavior
  - The endpoint runs the ADK agents and wraps `strategic_resume_agent(...)` in `asyncio.wait_for(..., timeout=65.0)`. The agent implementation itself imposes a runner timeout of 60s. Depending on model latency and environment, you may see 504 Gateway errors if agents don't finish in time. Consider increasing the timeouts for long-running analysis or using the mock ADK for local testing.
  - For local functional testing (without real Google ADK), set the environment variable `USE_MOCK_ADK=true` so the `mock_adk` implementation is used; this avoids needing external LLM connections and should finish quickly.

- Cloudinary / PDF upload
  - The code tries to generate and upload a PDF via `upload_to_cloudinary`. If Cloudinary credentials are missing, the code handles `cloudinary_url` possibly being None but you should verify credentials when testing the full flow.

How to reproduce verification locally (once SSL issue is fixed)
--------------------------------------------------------------
1. Ensure Python/ssl is fixed (follow one remediation above).
2. From project root, install dependencies if not already installed (poetry or pip):

```bash
poetry install --no-interaction
```

3. Start the server:

```bash
uvicorn main:app --reload --port 8000
```

4. Run the provided test script that sends a multipart request and tiny test image:

```bash
python3 test_strategic_endpoint.py
```

5. If you get a 504, check the server logs for agent timeouts. For quicker, deterministic tests, run with mocked ADK:

```bash
export USE_MOCK_ADK=true
uvicorn main:app --reload --port 8000
python3 test_strategic_endpoint.py
```

Checklist against your request
-----------------------------
- Make a call to the strategic analysis endpoint and see what the issue is: Partially done — I attempted to start the server and call the endpoint, but server startup failed; the root blocking issue (ImportError due to missing OpenSSL) was identified and reproduced locally. Status: Done (identified), cannot complete HTTP call until SSL issue resolved.
- Write a comprehensive analysis in docs with a solution: Done — this file.

Next recommended actions (priority order)
----------------------------------------
1. Fix Python/OpenSSL as shown in Option A or Option B so the server can start.
2. Start the server and run `test_strategic_endpoint.py`. Confirm successful response or capture any new errors (agent timeouts, JSON parsing errors, Cloudinary upload issues).
3. If agent responses lead to schema repairs or empty arrays, run `debug_strategic_endpoint.ipynb` and check `app/agents/resume/strategic/schema_assembler.py` (already used by `create_resume_from_fragments`) to see repair logs.
4. For development, use `export USE_MOCK_ADK=true` to avoid external LLMs and enable fast, repeatable tests.

If you'd like, I can now:
- Apply a local fix proposal (example: add a short note to README or helper script to install openssl and rebuild Python), or
- After you allow me to start the server again, re-run the test and capture endpoint errors beyond this SSL issue.

---
File generated by automated repo analysis on behalf of the project owner.
