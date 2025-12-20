# Setup and environment variables

Copy the example variables into a `.env` file at project root (do NOT commit `.env`).

Example `.env` contents:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
REPLICATE_API_KEY=your_replicate_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

Direnv auto-activation

1. Install `direnv`:
   - macOS (Homebrew): `brew install direnv`
   - Ubuntu/Debian: `sudo apt install direnv`
   - Windows: use WSL or `scoop`/`choco` as preferred

2. Hook direnv into your shell (one-time):
   - Bash / Zsh: add `eval "$(direnv hook bash)"` or `eval "$(direnv hook zsh)"` to your shell rc (`~/.bashrc` / `~/.zshrc`).

3. Approve project `.envrc`:
   - In project root run: `direnv allow`

Notes:
- `.envrc` will create/activate `.venv` and source `.env` if present.
- After `direnv allow`, opening a new terminal (or `cd` out and back in) should auto-activate the venv.


