import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config


class DBHandler:
    def __init__(self):
        self.conn = psycopg2.connect(Config.DATABASE_URL)

    def insert_image(self, filename: str, s3_key: str, s3_bucket: str):
        """Insert image record and return ID"""
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO images (filename, s3_key, s3_bucket) 
                   VALUES (%s, %s, %s) RETURNING id""",
                (filename, s3_key, s3_bucket),
            )
            result = cur.fetchone()
            if not result:
                raise Exception("Failed to insert image record")
            image_id = result[0]
            self.conn.commit()
            return image_id

    def insert_extracted_text(self, image_id: int, text_content: str):
        """Insert extracted text for an image"""
        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO extracted_text (image_id, text_content) 
                   VALUES (%s, %s)""",
                (image_id, text_content),
            )
            self.conn.commit()

    def get_unprocessed_images(self):
        """Get images without extracted text"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT i.id, i.filename, i.s3_key, i.s3_bucket 
                   FROM images i 
                   LEFT JOIN extracted_text et ON i.id = et.image_id 
                   WHERE et.id IS NULL 
                   ORDER BY i.created_at"""
            )
            return cur.fetchall()

    def get_stats(self):
        """Get processing statistics"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT
                    COUNT(DISTINCT i.id) as total_images,
                    COUNT(DISTINCT et.image_id) as processed_images
                   FROM images i
                   LEFT JOIN extracted_text et ON i.id = et.image_id"""
            )
            return cur.fetchone()

    def get_all_images_with_text(self):
        """Get all images with their extracted text (if any)"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT
                    i.id, i.filename, i.s3_key, i.s3_bucket, i.created_at,
                    et.text_content, et.extracted_at as text_created_at
                   FROM images i
                   LEFT JOIN extracted_text et ON i.id = et.image_id
                   ORDER BY i.created_at DESC"""
            )
            return cur.fetchall()

    def delete_image(self, image_id: int):
        """Delete an image and its extracted text"""
        with self.conn.cursor() as cur:
            # Delete extracted text first (foreign key constraint)
            cur.execute("DELETE FROM extracted_text WHERE image_id = %s", (image_id,))
            # Delete the image record
            cur.execute("DELETE FROM images WHERE id = %s", (image_id,))
            self.conn.commit()

    def close(self):
        self.conn.close()
