from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from storage_client.client import delete_file, file_exists, upload_file

TEST_PATH = "b2-connection-test/ping.txt"
TEST_CONTENT = b"Backblaze B2 connection test from Tender AI Screening.\n"


class Command(BaseCommand):
    help = "Upload a small test file to Backblaze B2, print its URL, then delete it."

    def handle(self, *args, **options):
        self.stdout.write(f"Uploading {TEST_PATH} ...")
        url = upload_file(ContentFile(TEST_CONTENT), TEST_PATH)
        self.stdout.write(self.style.SUCCESS(f"Uploaded. URL: {url}"))

        self.stdout.write(f"file_exists() -> {file_exists(TEST_PATH)}")

        delete_file(TEST_PATH)
        if file_exists(TEST_PATH):
            self.stdout.write(self.style.WARNING("Cleanup: file still exists after delete."))
        else:
            self.stdout.write(self.style.SUCCESS("Cleanup: test file deleted."))
