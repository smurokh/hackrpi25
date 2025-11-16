Run our project.
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
4. Running the project
   Run:
  ```
  python launcher.py
  ```
