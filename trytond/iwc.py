# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import threading
import json
from urllib.parse import urlparse
import logging
from collections import defaultdict, OrderedDict
import select

from trytond.pool import Pool
from trytond.config import config
from trytond import backend

logger = logging.getLogger(__name__)

iwc_on = os.environ.get('COOG_IWC', None) == '1'
broker = None


class Listener:
    _listener = {}
    _listener_lock = defaultdict(threading.Lock)

    @classmethod
    def run(cls, dbname):
        database = backend.Database(dbname)
        if database.has_channel():
            pid = os.getpid()
            with cls._listener_lock[pid]:
                if (pid, dbname) not in cls._listener:
                    cls._listener[pid, dbname] = listener = threading.Thread(
                        target=cls._listen, args=(dbname,), daemon=True)
                    listener.start()

    @classmethod
    def _listen(cls, dbname):
        database = backend.Database(dbname)
        if not database.has_channel():
            raise NotImplementedError

        logger.info("listening on channel ir_update of '%s'", dbname)
        conn = database.get_connection()
        pid = os.getpid()
        current_thread = threading.current_thread()
        try:
            cursor = conn.cursor()
            cursor.execute('LISTEN "ir_update"')
            conn.commit()

            while cls._listener.get((pid, dbname)) == current_thread:
                readable, _, _ = select.select([conn], [], [])
                if not readable:
                    continue

                conn.poll()
                while conn.notifies:
                    notification = conn.notifies.pop()
                    if notification.payload:
                        reset = json.loads(notification.payload)
                        for name in reset:
                            me = get_worker_id()
                            if 'init_pool' in name and me != name.split(
                                    '|')[-1]:
                                cls.on_init_pool(dbname)
        except Exception:
            logger.error(
                "IWC listener on '%s' crashed", dbname, exc_info=True)
            raise
        finally:
            database.put_connection(conn)
            with cls._listener_lock[pid]:
                if cls._listener.get((pid, dbname)) == current_thread:
                    del cls._listener[pid, dbname]

    @classmethod
    def on_init_pool(cls, dbname):
        logger.info('Reload pool catched(%s)', dbname)
        Pool.stop(dbname)
        Pool(dbname).init()

    @classmethod
    def stop(cls):
        to_join = []
        current_pid = os.getpid()
        with cls._listener_lock[current_pid]:
            for pid, dbname in list(cls._listener):
                if pid != current_pid:
                    continue
                to_join.append(cls._listener.pop((pid, dbname), None))
                try:
                    database = backend.Database(dbname)
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute('NOTIFY ir_update')
                    conn.commit()
                finally:
                    database.put_connection(conn)
        for listener in to_join:
            listener.join()


def get_worker_id():
    return '%s-%s' % (os.environ.get('HOSTNAME', 'localhost'), os.getpid())


def broadcast_init_pool(dbname):
    database = backend.Database(dbname)
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'NOTIFY "%s", %%s' % 'ir_update',
            (json.dumps(['init_pool|%s' % get_worker_id()],
                separators=(',', ':')),))
        conn.commit()
    finally:
        database.put_connection(conn)
    logger.info('init_pool(%s)', dbname)


def start(db_name):
    global iwc_on
    if not iwc_on:
        return
    Listener.run(db_name)


def stop():
    global iwc_on
    if not iwc_on:
        return
    logger.info('init_pool: %s stopping')
    Listener.stop()
