import os
from pathlib import Path

import frontmatter
import yaml
from slugify import slugify


def represent_none(self, _):
    # This forces PyYAML to represent None as an empty scalar (blank)
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)
yaml.SafeDumper.add_representer(type(None), represent_none)

# CONFIGURATION
VAULT_PATH = Path(os.getenv("TWELVE_INPUT")) / "recipes"


def update_tags(tags_data):
    """
    Standardizes tags into a list, renames 'Post' to 'post',
    and ensures 'post' is present.
    """
    # Handle cases where tags: is empty or missing
    if not tags_data:
        return ["posts"]

    # Handle case where tags: some-string (single tag)
    if isinstance(tags_data, str):
        tags_data = [tags_data]

    # Normalize: rename 'Post' or 'posts' to 'post', keep others as-is
    # Using a set to ensure uniqueness
    new_tags = set()
    for t in tags_data:
        if slugify(t) in ["post", "posts"]:
            new_tags.add("posts")
        elif slugify(t) in ["recipes", "recipe"]:
            new_tags.add("recipes")
        else:
            new_tags.add(slugify(t))

    # Final check: ensure 'post' is definitely in there
    new_tags.add("posts")
    new_tags.add("recipes")

    return list(new_tags)


def process_vault():
    # Recursively find all markdown files
    for path in Path(VAULT_PATH).rglob("*.md"):
        try:
            # Load the file
            post = frontmatter.load(path)

            # Access the 'tags' key in the frontmatter dictionary
            current_tags = post.metadata.get("tags")

            # Update the tags using our logic
            post.metadata["tags"] = update_tags(current_tags)

            # Write the changes back to the file
            # .dump() preserves the content body and only updates frontmatter
            with open(path, "wb") as f:
                frontmatter.dump(post, f, Dumper=yaml.SafeDumper)

            print(f"✅ Updated: {path.name}")

        except Exception as e:
            print(f"❌ Error processing {path.name}: {e}")


if __name__ == "__main__":
    process_vault()
