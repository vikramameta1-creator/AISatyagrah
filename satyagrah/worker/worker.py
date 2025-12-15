import os
from redis import Redis
from rq import Queue, SimpleWorker  # Windows-safe worker (no fork)

def main() -> None:
    url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    conn = Redis.from_url(url)
    q = Queue("exports", connection=conn)
    w = SimpleWorker([q], connection=conn)
    w.work(with_scheduler=False, burst=False)

if __name__ == "__main__":
    main()
