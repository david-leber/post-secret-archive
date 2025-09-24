from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from utils.s3_handler import S3Handler
from utils.db_handler import DBHandler
from config import Config

from typing import Any
from werkzeug.datastructures import FileStorage

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
    """Upload image to S3 and create DB record"""
    LOG.info(f"POST request received. Files: {list(request.files.keys())}")
    if "file" not in request.files:
        LOG.error("No 'file' key in request.files")
        flash("No file selected", "error")
        return redirect(request.url)

    file: FileStorage = request.files["file"]
    LOG.info(f"File received: {file.filename}")
    if file.filename is None or file.filename == "":
        LOG.error("File has no filename")
        flash("No file selected", "error")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        LOG.info(f"Accepted file {file.filename}")
        filename = secure_filename(file.filename)
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

            flash(f"Image uploaded successfully! ID: {image_id}", "success")
            return redirect(url_for("extract", image_id=image_id))
        except Exception as e:
            flash(f"Error uploading file: {str(e)}", "error")
            return redirect(request.url)
    else:
        message = (
            "Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp, tifferror"
        )
        LOG.error(message)
        flash(message)
        return redirect(request.url)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
