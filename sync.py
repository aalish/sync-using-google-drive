import os
import time
import zipfile
import logging
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Google Drive API Setup
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = './service-account.json'  # Replace with your service account JSON file path

# Initialize Google Drive API
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

# Configuration File Path
CONFIG_FILE = './config.json'  # Replace with your configuration file path

# Backup Folder in Google Drive
BACKUP_FOLDER_ID = '1WYgGglbHxds7Ajy2Omdpk8WvyN1u69xY'  # Replace with your Google Drive backup folder ID
BACKUP_INTERVAL_DAYS = 10  # Interval for creating backups


def load_config():
    """Load file paths and folder paths from the configuration file."""
    try:
        with open(CONFIG_FILE, 'r') as config_file:
            logging.info("Configuration file loaded successfully.")
            return json.load(config_file)
    except Exception as e:
        logging.error(f"Failed to load configuration file: {e}")
        raise


def list_files_in_drive(folder_id):
    """List all files in the specified Google Drive folder."""
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
        logging.info(f"Listed files in Google Drive folder ID {folder_id}.")
        return results.get('files', [])
    except Exception as e:
        logging.error(f"Failed to list files in Drive: {e}")
        raise


def upload_file(file_path, drive_files, folder_id):
    """Upload a file to Google Drive if it's newer or not present."""
    file_name = os.path.basename(file_path)
    local_modified_time = os.path.getmtime(file_path)

    try:
        drive_file = next((f for f in drive_files if f['name'] == file_name), None)
        if drive_file:
            drive_modified_time = datetime.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
            if local_modified_time <= drive_modified_time:
                logging.info(f"No upload needed for {file_name}, Drive version is up-to-date.")
                return

            media = MediaFileUpload(file_path, resumable=True)
            service.files().update(fileId=drive_file['id'], media_body=media).execute()
            logging.info(f"Updated file: {file_name} in Google Drive.")
        else:
            media = MediaFileUpload(file_path, resumable=True)
            file_metadata = {'name': file_name, 'parents': [folder_id]}
            service.files().create(body=file_metadata, media_body=media).execute()
            logging.info(f"Uploaded new file: {file_name} to Google Drive.")
    except Exception as e:
        logging.error(f"Failed to upload file {file_name}: {e}")
        raise


def download_file(file_name, drive_file):
    """Download a file from Google Drive if it's newer or not present locally."""
    config = load_config()
    file_mapping = config['file_mappings']
    local_file_path = file_mapping.get(file_name)

    if not local_file_path:
        logging.warning(f"File {file_name} is not mapped for local sync.")
        return

    try:
        drive_modified_time = datetime.strptime(drive_file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
        if os.path.exists(local_file_path):
            local_modified_time = os.path.getmtime(local_file_path)
            if local_modified_time >= drive_modified_time:
                logging.info(f"No download needed for {file_name}, local version is up-to-date.")
                return

        request = service.files().get_media(fileId=drive_file['id'])
        with open(local_file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        logging.info(f"Downloaded file: {file_name} from Google Drive.")
    except Exception as e:
        logging.error(f"Failed to download file {file_name}: {e}")
        raise


def create_backup():
    """Create a zip backup of all configured files and upload to Google Drive if the last backup is older than the interval."""
    now = datetime.now()
    backup_files_in_drive = list_files_in_drive(BACKUP_FOLDER_ID)

    # Find the most recent backup file
    recent_backup = None
    for file in backup_files_in_drive:
        modified_time = datetime.strptime(file['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if not recent_backup or modified_time > datetime.strptime(recent_backup['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ'):
            recent_backup = file

    if recent_backup:
        recent_backup_time = datetime.strptime(recent_backup['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if now - recent_backup_time < timedelta(days=BACKUP_INTERVAL_DAYS):
            logging.info(f"Skipping backup: Last backup {recent_backup_time} is within the interval.")
            return

    backup_file_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    local_backup_path = os.path.join("/tmp", backup_file_name)

    try:
        config = load_config()
        files_to_backup = config['file_mappings'].values()

        # Create a zip file for backup
        with zipfile.ZipFile(local_backup_path, 'w') as backup_zip:
            for file_path in files_to_backup:
                if os.path.exists(file_path):
                    backup_zip.write(file_path, os.path.basename(file_path))
        logging.info(f"Backup created locally: {local_backup_path}")

        # Upload the backup to Google Drive
        upload_file(local_backup_path, backup_files_in_drive, BACKUP_FOLDER_ID)

        # Remove the local backup file after upload
        os.remove(local_backup_path)
        logging.info("Local backup file deleted after upload.")
    except Exception as e:
        logging.error(f"Failed to create or upload backup: {e}")
        raise


def sync():
    """Sync files between local folder and Google Drive."""
    try:
        config = load_config()
        drive_files = list_files_in_drive(config['folder_id'])

        for file_path in config['file_mappings'].values():
            if os.path.isfile(file_path):
                upload_file(file_path, drive_files, config['folder_id'])

        for drive_file in drive_files:
            download_file(drive_file['name'], drive_file)

        logging.info("Sync operation completed.")
    except Exception as e:
        logging.error(f"Failed during sync operation: {e}")
        raise


if __name__ == "__main__":
    last_backup_time = datetime.now() - timedelta(days=BACKUP_INTERVAL_DAYS)

    while True:
        logging.info("Starting sync operation...")
        sync()

        if datetime.now() - last_backup_time >= timedelta(days=BACKUP_INTERVAL_DAYS):
            logging.info("Creating backup...")
            create_backup()
            last_backup_time = datetime.now()

        logging.info("Sync complete. Waiting 5 minutes before next sync.")
        time.sleep(300)  # Wait 5 minutes before the next sync
