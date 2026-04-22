# twelve
Static sites with an extra "push". My own static site generator, inspired by eleventy, in Python.

# Content Requirements

... TODO ...

# Site project structure

Twelve expects a specific structure for processing files and building a site.

### Project Structure

```text
root/
├── input/
│   ├── _assets/
│   ├── _data/
│   ├── _layouts/
│   ├── _templates/
│   ├──  - - links/   <-- (Optional)
│   ├──  - - posts/   <-- (Optional)
│   └── pages/
└── output/
```

---

### Directory Descriptions

* **`input/`**
    The source directory containing all your raw development files, configurations, and content.
    * **`_assets/`**: Raw frontend files like CSS, JS, and images.
    * **`_data/`**: Global data files (JSON/YAML) used to populate templates.
    * **`_layouts/`**: Content-specific layouts.
    * **`_templates/`**: Reusable components and partials.
    * **`pages/`**: Individual content files and site routes.
    * **`links/` (Optional)**: Often used for managing external resources, bookmarks, or a "link-in-bio" style collection of redirects.
    * **`posts/` (Optional)**: The standard home for chronological content, such as blog entries or news updates, usually sorted by date.
* **`output/`**
    The destination directory where your build process generates the final, production-ready files. This folder is typically what gets deployed to a web server and is often excluded from version control (via `.gitignore`) since it is auto-generated.


Other than the reserved folder names described above, you can organize content anywhere you like. Twelve relies on the `permalink` specified in the frontmatter for each page.


# Environment variables

Building sites requires a `-i --input` and `-o --output` directory. These can be stored as environment variables

```env
TWELVE_INPUT="/Users/yourname/projects/my-vault"
TWELVE_OUTPUT="/Users/yourname/projects/my-vault/.site"
```

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