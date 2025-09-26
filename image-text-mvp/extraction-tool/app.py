from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from utils.s3_handler import S3Handler
from utils.db_handler import DBHandler
from config import Config

from typing import Any

import logging
import sys

# Configure logging to stdout with INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

LOG = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """Dashboard showing stats and options"""
    db = DBHandler()
    stats = db.get_stats()
    db.close()
    return render_template("dashboard.html", stats=stats)


@app.route("/upload", methods=["GET"])
def upload():
    """Show upload form"""
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_post():
    """Upload multiple images to S3 and create DB records"""
    LOG.info(f"POST request received. Files: {list(request.files.keys())}")
    if "files" not in request.files:
        LOG.error("No 'files' key in request.files")
        flash("No files selected", "error")
        return redirect(request.url)

    files = request.files.getlist("files")
    LOG.info(f"Files received: {[f.filename for f in files]}")

    if not files or all(f.filename == "" for f in files):
        LOG.error("No files selected")
        flash("No files selected", "error")
        return redirect(request.url)

    uploaded_images: list[dict[str, int | str]] = []
    errors: list[str] = []

    for file in files:
        if file.filename and allowed_file(file.filename):
            LOG.info(f"Processing file {file.filename}")
            filename = clean_file_name(file.filename)
            s3_key = f"images/{filename}"

            try:
                # Upload to S3
                s3_handler = S3Handler()
                file.seek(0)  # Reset file pointer
                s3_url = s3_handler.upload_file(file, s3_key)
                LOG.info(f"File uploaded to S3: {s3_url}")

                # Save to database
                db = DBHandler()
                image_id = db.insert_image(filename, s3_key, Config.S3_BUCKET_NAME)
                db.close()
                LOG.info(f"Saved to DB with {image_id=}")

                uploaded_images.append({"id": image_id, "filename": filename})
            except Exception as e:
                LOG.error(f"Error uploading {file.filename}: {str(e)}")
                errors.append(f"Error uploading {file.filename}: {str(e)}")
        else:
            if file.filename:
                error_msg = f"Invalid file type for {file.filename}. Allowed types: png, jpg, jpeg, gif, bmp, tiff"
                LOG.error(error_msg)
                errors.append(error_msg)

    # Show results to user
    if uploaded_images:
        flash(f"Successfully uploaded {len(uploaded_images)} image(s)!", "success")

        # If errors occurred, show them too
        if errors:
            for error in errors:
                flash(error, "error")

        # Redirect to first uploaded image for processing
        return redirect(url_for("extract", image_id=uploaded_images[0]["id"]))
    else:
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            flash("No valid images were uploaded", "error")
        return redirect(request.url)


def clean_file_name(file: str) -> str:
    secure_name = secure_filename(file)

    # Remove any extra . characters to prevent issues
    if secure_name.count(".") > 1:
        parts = secure_name.split(".")
        secure_name = "_".join(parts[:-1]) + "." + parts[-1]
    LOG.info(f"Cleaned filename: {secure_name}")
    return secure_name


@app.route("/extract/<int:image_id>", methods=["GET"])
def extract(image_id: int):
    """Show text extraction form for image"""
    db = DBHandler()

    # Get image details
    with db.conn.cursor() as cur:
        LOG.info("Querying for image with ID %s", image_id)
        cur.execute(
            "SELECT id, filename, s3_key, s3_bucket FROM images WHERE id = %s",
            (image_id,),
        )
        image = cur.fetchone()

    if not image:
        LOG.error(f"Image with ID {image_id} not found")
        flash("Image not found", "error")
        db.close()
        return redirect(url_for("index"))

    # Get image URL
    s3_handler = S3Handler()
    image_url = s3_handler.get_file_url(image[2])  # s3_key
    LOG.info(f"Image URL: {image_url}")

    # Get stats for progress
    stats = db.get_stats()
    db.close()

    image_data: dict[str, Any] = {
        "id": image[0],
        "filename": image[1],
        "url": image_url,
    }

    return render_template("extract.html", image=image_data, stats=stats)


@app.route("/extract/<int:image_id>", methods=["POST"])
def extract_post(image_id: int):
    """Process extracted text from uploaded image"""
    db = DBHandler()
    text_content = request.form.get("text_content", "").strip()

    if text_content:
        try:
            db.insert_extracted_text(image_id, text_content)
            flash("Text extracted and saved successfully!", "success")

            # Check if there are more unprocessed images
            unprocessed = db.get_unprocessed_images()
            db.close()

            if unprocessed:
                return redirect(url_for("extract", image_id=unprocessed[0]["id"]))
            else:
                return redirect(url_for("index"))
        except Exception as e:
            flash(f"Error saving text: {str(e)}", "error")
            db.close()
            return redirect(request.url)
    else:
        flash("Please enter some text", "error")
        return redirect(request.url)


@app.route("/batch")
def batch():
    """Show all unprocessed images for batch processing"""
    db = DBHandler()
    unprocessed = db.get_unprocessed_images()
    stats = db.get_stats()
    LOG.info(f"Stats: {stats}")
    db.close()

    if unprocessed:
        # Redirect to first unprocessed image
        return redirect(url_for("extract", image_id=unprocessed[0]["id"]))
    else:
        flash("All images have been processed!", "success")
        return redirect(url_for("index"))


@app.route("/admin")
def admin_tools():
    """Show admin tools page"""
    return render_template("admin_tools.html")


@app.route("/admin/images")
def view_all_images():
    """Show all images with their extracted text"""
    db = DBHandler()
    images = db.get_all_images_with_text()

    # Get image URLs from S3
    s3_handler = S3Handler()
    for image in images:
        image["url"] = s3_handler.get_file_url(image["s3_key"])

    db.close()
    return render_template("view_all_images.html", images=images)


@app.route("/admin/delete_image/<int:image_id>", methods=["POST"])
def delete_image(image_id: int):
    """Delete an image and its extracted text"""
    db = DBHandler()
    try:
        db.delete_image(image_id)
        flash("Image deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting image: {str(e)}", "error")
    finally:
        db.close()

    return redirect(url_for("view_all_images"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
