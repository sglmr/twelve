import os

from PIL import Image, ImageSequence
from pillow_heif import register_heif_opener

# Register modern mobile formats
register_heif_opener()


def process_photo_collection(directory):
    # Supported formats (excluding PDF)
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".avif", ".tiff", ".bmp", ".gif"}
    PROCESSED_COMMENT = "xprocessed"

    output_dir = os.path.join(directory, "web_optimized")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(directory):
        if not filename.lower().endswith(extensions):
            continue

        input_path = os.path.join(directory, filename)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.webp")

        try:
            img = Image.open(input_path)

            with img:
                # 2. Check for our marker tag
                if img.info.get("comment") == PROCESSED_COMMENT.encode("utf-8"):
                    print(f"⏩ Skipping {filename}: Already processed.")
                    continue

                # 3. Handle Animation vs Static
                is_animated = getattr(img, "is_animated", False)
                max_size = 1600

                if is_animated:
                    frames = []
                    for frame in ImageSequence.Iterator(img):
                        f = frame.copy().convert("RGBA")
                        if max(f.size) > max_size:
                            f.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        frames.append(f)

                    frames[0].save(
                        output_path,
                        "WEBP",
                        save_all=True,
                        append_images=frames[1:],
                        quality=80,
                        comment=PROCESSED_COMMENT,
                        duration=img.info.get("duration", 100),
                        loop=img.info.get("loop", 0),
                    )
                else:
                    # Standard Image logic
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGBA")  # Keep transparency for PNG/GIF
                    else:
                        img = img.convert("RGB")

                    if max(img.size) > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                    img.save(output_path, "WEBP", quality=80, comment=PROCESSED_COMMENT)

                print(f"✅ Finished: {filename} -> {base_name}.webp")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")


if __name__ == "__main__":
    process_photo_collection("./my_photos_folder")
