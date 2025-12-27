import os
import uvicorn

from satyagrah.web.jobs_api import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "9000"))
    uvicorn.run(app, host=host, port=port, log_level="info")
