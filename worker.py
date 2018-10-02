"""
Generic worker.py for enabling background workers to run
long jobs.  Nothing to change or modify here.
"""

import os

import redis
from rq import Worker, Queue, Connection

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDISTOGO_URL', 'redis://redistogo:1d06e8e4ef4e3aa0519d2ee323b2d83d@spinyfin.redistogo.com:10598/')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
