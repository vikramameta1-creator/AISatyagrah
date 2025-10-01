from pathlib import Path
from .models import Job, ResultManifest, ResultItem
import json, zipfile, mimetypes

def write_job_zip(job: Job, zip_path: Path) -> None:
    # write manifest.json + tasks.json (if you want), minimal

def list_result_zip(zip_path: Path) -> ResultManifest:
    with zipfile.ZipFile(zip_path, "r") as zf:
        items = []
        for n in zf.namelist():
            info = zf.getinfo(n)
            items.append(ResultItem(name=n, size=info.file_size,
                        mime=mimetypes.guess_type(n)[0] or "application/octet-stream"))
    return ResultManifest(job_id=zip_path.stem.replace("result_", ""), items=items)
