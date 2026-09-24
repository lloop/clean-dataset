import json

with open("dataset_dirty/metadata/manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

target_files = {
    "AUDIT.xml",
    "Data.csv",
    "Notes.json",
    "PHOTO_COPY.csv",
    "Schedule.py",
    "Statement_1.csv",
    "TIMESHEET_OLD.xml",
    "audit.xml",
    "backup_draft.csv",
    "brief_backup_1.json",
    "brief_backup_1_copy.json",
    "data.json",
    "data_2.py",
    "invoice_draft.csv",
    "project.py",
    "report-.xml",
    "BACKUP.html",
    "audit_old.csv",
}

for record in manifest["files"]:
    if record.get("filename") in target_files:
        print(json.dumps(record, indent=2))