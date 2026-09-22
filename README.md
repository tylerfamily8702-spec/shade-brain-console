# shade-brain-console

Status and configuration hub for the shade-brain / shade-ai stack running on umbra.

## Repo layout

```
status-console.html      dashboard UI
status-poller.py         local API the dashboard reads from
config/                   the shade-ai systemd container set
scripts/                  provisioning / bootstrap script
```

---

## status-console.html

The dashboard page. Shows a green/red status dot for each service
(qdrant, litellm, open-webui, ollama) and a tail of recent log lines
for whichever service is failing, so you can see what broke without
digging through journalctl yourself.

**Use it:** open the file in a browser (or serve it) while
`status-poller.py` is running. No install needed, it's static HTML/JS.

## status-poller.py

The backend the console talks to. Runs a small local HTTP server at
`http://localhost:8765/status`. On each request it:
- hits each service's health endpoint (qdrant :6333, litellm :4000/health,
  open-webui :8080/health, ollama :11434) with a 2s timeout
- pulls the last 20 lines from each service's user systemd journal
  (`journalctl --user -u <unit> -n 20`)
- prefers error-looking lines (error, failed, timeout, refused, etc.)
  over plain recent lines when picking what to show

**Use it:**
```
python3 status-poller.py
```
Then point status-console.html at `http://localhost:8765/status`.

---

## config/ - shade-ai systemd container set

Podman/systemd quadlet files that define the actual running stack. This
is the infrastructure the poller checks the health of.

- `shade-ai.pod` - the pod definition; groups the containers below so
  they share a network namespace and come up/down together
- `shade-ai.network` - the podman network the pod attaches to
- `ollama.container` - runs Ollama, serving the local model
- `litellm.container` - LiteLLM proxy in front of Ollama (uses
  `litellm-config.yaml`), gives an OpenAI-compatible API surface
- `qdrant.container` - the vector DB for memory/embeddings
- `open-webui.container` - the chat UI in front of the models
- `tailscale.container` - Tailscale sidecar, exposes the stack over
  your tailnet via `tailscale-serve.json` instead of opening ports
  publicly
- 5x `.volume` files - persistent storage definitions, one per
  service that needs to keep data across restarts (ollama models,
  qdrant data, open-webui data, litellm config, tailscale state)
- `.env` - shared environment variables the containers read at
  startup (API keys, ports, etc.) - **do not commit real secrets
  here**, use a `.env.example` with placeholders instead

**Use it:** these are systemd quadlet units. Copy the `.container`,
`.pod`, `.network`, and `.volume` files into
`~/.config/containers/systemd/` on umbra, put `.env`,
`litellm-config.yaml`, and `tailscale-serve.json` in
`~/.config/shade-ai/`, then:
```
systemctl --user daemon-reload
systemctl --user start shade-ai-pod
```

---

## scripts/ - provisioning script

The bootstrap script that sets a fresh box up to run the stack above.
It:
- creates a dedicated `shade` system user (so the stack doesn't run as
  your personal account)
- sets up the vault directory structure under the shade user's home
- installs Ollama and the Python dependencies Cognee (memory layer)
  needs
- runs a smoke test at the end to confirm the pieces came up clean

**Use it:** run once on a new/rebuilt host, before starting the
containers in `config/`:
```
sudo bash scripts/shade-bootstrap.sh
```

---

## Not yet in this repo

Intentionally kept out of code for now:
- family bank / grants / LLC planning - lives in ClickUp and personal
  notes, not code
- AI-skills screening notes (Anthropic Skills, BMAD Method, Archon,
  etc.) - still notes, not implemented tooling
