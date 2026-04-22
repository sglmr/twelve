# twelve
Static sites with an extra "push". My own static site generator, inspired by eleventy, in Python.


# Local installation

## Install with uv

Install locally and editable with uv:

```sh
uv tool install --editable .
```

## Set Environment Variables

To make these stick across all terminal sessions, add the input and output environment variables to your user profile.

#### **On Windows (PowerShell/CMD)**
1.  Open the **Start Menu**, search for **"Edit the system environment variables"**, and hit Enter.
2.  Click **Environment Variables** at the bottom right.
3.  Under **User variables**, click **New**.
    * **Variable name:** `TWELVE_INPUT`
    * **Variable value:** `C:\Users\YourName\Documents\MyVault` (Use the full absolute path!)
4.  Repeat for `TWELVE_OUTPUT`.
5.  **Restart your terminal** for changes to take effect.

#### **On macOS or Linux (Zsh/Bash)**
1.  Open your config file (usually `~/.zshrc` or `~/.bashrc`) in an editor.
2.  Add these lines at the bottom:
    ```bash
    export TWELVE_INPUT="/Users/yourname/projects/my-vault"
    export TWELVE_OUTPUT="/Users/yourname/projects/my-vault/.site"
    ```
3.  Save and run `source ~/.zshrc` (or restart the terminal).