# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
import select
import signal
import time
from multiprocessing import Pool as MPool, cpu_count

from sql import Flavor

from trytond import backend
from trytond.config import config
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['work']
logger = logging.getLogger(__name__)
Database = backend.get('Database')
DatabaseOperationalError = backend.get('DatabaseOperationalError')


class Queue(object):
    def __init__(self, pool, mpool):
        self.database = Database(pool.database_name).connect()
        self.connection = self.database.get_connection(autocommit=True)
        self.pool = pool
        self.mpool = mpool

    def pull(self, name=None):
        Queue = self.pool.get('ir.queue')
        return Queue.pull(self.database, self.connection, name=name)

    def run(self, task_id):
        return self.mpool.apply_async(
            run_task, (self.pool.database_name, task_id))


class TaskList(list):
    def filter(self):
        for t in list(self):
            if t.ready():
                self.remove(t)
        return self


def work(options):
    Flavor.set(Database.flavor)
    if not config.getboolean('queue', 'worker', default=False):
        return
    try:
        processes = options.processes or cpu_count()
    except NotImplementedError:
        processes = 1
    logger.info("start %d workers", processes)
    mpool = MPool(
        processes, initializer, (options,), options.maxtasksperchild)
    queues = [Queue(pool, mpool) for pool in initializer(options, False)]

    tasks = TaskList()
    timeout = options.timeout
    try:
        while True:
            while len(tasks.filter()) >= processes:
                time.sleep(0.1)
            for queue in queues:
                task_id, next_ = queue.pull(options.name)
                timeout = min(
                    next_ or options.timeout, timeout, options.timeout)
                if task_id:
                    tasks.append(queue.run(task_id))
                    break
            else:
                connections = [q.connection for q in queues]
                connections, _, _ = select.select(connections, [], [], timeout)
                for connection in connections:
                    connection.poll()
                    while connection.notifies:
                        connection.notifies.pop(0)
    except KeyboardInterrupt:
        mpool.close()


def initializer(options, worker=True):
    if worker:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    pools = []
    database_list = Pool.database_list()
    for database_name in options.database_names:
        pool = Pool(database_name)
        if database_name not in database_list:
            with Transaction().start(database_name, 0, readonly=True):
                pool.init()
        pools.append(pool)
    return pools


def run_task(pool, task_id):
    if not isinstance(pool, Pool):
        pool = Pool(pool)
    Queue = pool.get('ir.queue')
    logger.info('task "%d" started', task_id)
    try:
        for count in range(config.getint('database', 'retry'), -1, -1):
            with Transaction().start(pool.database_name, 0) as transaction:
                try:
                    Queue(task_id).run()
                    break
                except DatabaseOperationalError:
                    if count:
                        transaction.rollback()
                        continue
                    raise
        logger.info('task "%d" done', task_id)
    except Exception:
        logger.critical('task "%d" failed', task_id, exc_info=True)
