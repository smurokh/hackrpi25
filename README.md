Quick setup (Unix / macOS)
1. Open a terminal in the project root.
2. Create a venv and activate it:
   - macOS / Linux (bash/zsh):
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Windows (cmd.exe):
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. Upgrade pip and install requirements:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
   
Running the project

- Run:
  ```python launcher.py
  ```
- Generate a simple top-level `launcher.py` that runs games in a sequence and consumes their JSON output, or
- Add a small script to validate `links.json` (detect dead links) and print a report.
