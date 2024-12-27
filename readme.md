# Google Drive Sync Script

This script synchronizes files between a local directory and Google Drive. It also supports creating periodic backups of specified files as zip archives, which are uploaded to a designated folder in Google Drive.

## Features
- Syncs files between local storage and Google Drive.
- Compares file modification timestamps to upload/download only the latest version.
- Automatically creates zip backups of specified files every 10 days.
- Logs all activities for easy debugging and monitoring.

## Prerequisites
1. **Python Environment**:
   - Ensure Python 3.7+ is installed.
   - Create and activate a virtual environment (optional but recommended).

     ```bash
     python3 -m venv /data/mine/sync_files/linux-env
     source /data/mine/sync_files/linux-env/bin/activate
     ```

2. **Install Required Libraries**:
   Install dependencies using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

3. **Google Drive API**:
   - Enable the Google Drive API for your project in the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a Service Account and download the credentials JSON file.
   - Replace `path/to/service-account.json` in the script with the actual path to your credentials file.

4. **Configuration File**:
   Create a `config.json` file with the following structure:

   ```json
   {
       "folder_id": "your-google-drive-folder-id",
       "file_mappings": {
           "file1.txt": "/local/path/to/file1.txt",
           "file2.docx": "/local/path/to/file2.docx"
       }
   }
   ```
   - `folder_id`: The ID of the main folder in Google Drive for synchronization.
   - `file_mappings`: A dictionary mapping filenames in Google Drive to their respective local file paths.

5. **Backup Folder**:
   Replace `your-backup-folder-id` in the script with the ID of the folder in Google Drive where backups should be stored.

## Running the Script
To run the script:

```bash
/data/mine/sync_files/linux-env/bin/python /path/to/script.py
```

## Running as a Background Service
To run the script as a background service:

### 1. Create a Systemd Service File

1. Create the service file:

   ```bash
   nano ~/.config/systemd/user/sync_files.service
   ```

2. Add the following content:

   ```ini
   [Unit]
   Description=Sync Files with Google Drive
   After=network.target

   [Service]
   Type=simple
   ExecStart=/data/mine/sync_files/linux-env/bin/python /path/to/script.py
   WorkingDirectory=/data/mine/sync_files/
   Restart=always
   RestartSec=10
   StandardOutput=append:/data/mine/sync_files/sync_files.log
   StandardError=append:/data/mine/sync_files/sync_files_error.log

   [Install]
   WantedBy=default.target
   ```

3. Save and exit.

### 2. Enable and Start the Service

1. Reload the systemd daemon:
   ```bash
   systemctl --user daemon-reload
   ```

2. Enable the service:
   ```bash
   systemctl --user enable sync_files.service
   ```

3. Start the service:
   ```bash
   systemctl --user start sync_files.service
   ```

4. Check the status:
   ```bash
   systemctl --user status sync_files.service
   ```

### 3. Enable Linger for Auto-Start
Ensure the service starts even when the user is not logged in:

```bash
loginctl enable-linger xero
```

## Logs
Logs are written to:
- **Standard Output**: `/data/mine/sync_files/sync_files.log`
- **Error Logs**: `/data/mine/sync_files/sync_files_error.log`

View logs with:
```bash
cat /data/mine/sync_files/sync_files.log
cat /data/mine/sync_files/sync_files_error.log
```

## License
This script is licensed under the MIT License.

