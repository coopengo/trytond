# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys
import os
import logging
from getpass import getpass
from filelock import FileLock

from sql import Table

from trytond.transaction import Transaction
from trytond import backend
from trytond.pool import Pool
from trytond.config import config

from trytond.modules import get_module_info

__all__ = ['run']
logger = logging.getLogger(__name__)

# XUNG
def _check_update_needed(db_name, options, transaction):
    # Get current main module version
    main_module = config.get('version', 'module', default='coog_core')
    current_main_module_version = get_module_info(main_module)['version']

    # Do the upgrade anyway if -u is activated
    if options.update:
        return True, current_main_module_version

    # Get main module version which stocked in the database
    version_control_table = Table('upgrade_version_control')
    cursor = transaction.connection.cursor()
    cursor.execute(*version_control_table.select(version_control_table.current_version))
    db_main_module_version = cursor.fetchone()[0]

    if options.check_update and current_main_module_version != db_main_module_version:
        return True, current_main_module_version

    return False, current_main_module_version

def run(options):
    Database = backend.get('Database')
    main_lang = config.get('database', 'language')
    init = {}
    for db_name in options.database_names:
        init[db_name] = False
        database = Database(db_name)
        database.connect()
        if options.update:
            if not database.test():
                logger.info("init db")
                database.init()
                init[db_name] = True
        elif not database.test():
            raise Exception('"%s" is not a Tryton database.' % db_name)

    for db_name in options.database_names:
        if options.update:
            with Transaction().start(db_name, 0) as transaction,\
                    transaction.connection.cursor() as cursor:
                database = Database(db_name)
                database.connect()
                if not database.test():
                    raise Exception('"%s" is not a Tryton database.' % db_name)
                lang = Table('ir_lang')
                cursor.execute(*lang.select(lang.code,
                        where=lang.translatable == True))
                lang = set([x[0] for x in cursor.fetchall()])
            lang.add(main_lang)
        else:
            lang = set()

        lang |= set(options.languages)
        pool = Pool(db_name)

        # XUNG
        with Transaction().start(db_name, 0) as transaction:
            # Create a lock file
            # This lock will block others workers /
            # processes until the current upgrade is finished
            lock_file_name = '/tmp/version_control_lock.lck'
            with FileLock(lock_file_name) as version_control_lock:
                version_control_lock.acquire()
                is_upgrade_needed, new_version = _check_update_needed(db_name,
                    options, transaction)
                if not is_upgrade_needed:
                    options.update = []
                    options.check_update = []
                pool.init(update=options.update or options.check_update,
                    lang=list(lang), activatedeps=options.activatedeps)
                if is_upgrade_needed:
                    # If upgrade finishes correctly->update version in database
                    try:
                        version_control_table = Table('upgrade_version_control')
                        cursor = transaction.connection.cursor()
                        cursor.execute(*version_control_table.update(
                            columns=[version_control_table.current_version],
                            values=[new_version]))
                        transaction.commit()

                    except:
                        transaction.rollback()
                        raise
                version_control_lock.release()

        if options.update_modules_list:
            with Transaction().start(db_name, 0) as transaction:
                Module = pool.get('ir.module')
                Module.update_list()

        if lang:
            with Transaction().start(db_name, 0) as transaction:
                pool = Pool()
                Lang = pool.get('ir.lang')
                languages = Lang.search([
                        ('code', 'in', lang),
                        ])
                Lang.write(languages, {
                        'translatable': True,
                        })

    for db_name in options.database_names:
        with Transaction().start(db_name, 0) as transaction:
            pool = Pool()
            User = pool.get('res.user')
            Configuration = pool.get('ir.configuration')
            configuration = Configuration(1)
            with transaction.set_context(active_test=False):
                admin, = User.search([('login', '=', 'admin')])

            if options.email is not None:
                admin.email = options.email
            elif init[db_name]:
                admin.email = input(
                    '"admin" email for "%s": ' % db_name)
            if init[db_name] or options.password:
                configuration.language = main_lang
                # try to read password from environment variable
                # TRYTONPASSFILE, empty TRYTONPASSFILE ignored
                passpath = os.getenv('TRYTONPASSFILE')
                password = ''
                if passpath:
                    try:
                        with open(passpath) as passfile:
                            password, = passfile.read().splitlines()
                    except Exception as err:
                        sys.stderr.write('Can not read password '
                            'from "%s": "%s"\n' % (passpath, err))

                if not password and not options.reset_password:
                    while True:
                        password = getpass(
                            '"admin" password for "%s": ' % db_name)
                        password2 = getpass('"admin" password confirmation: ')
                        if password != password2:
                            sys.stderr.write('"admin" password confirmation '
                                'doesn\'t match "admin" password.\n')
                            continue
                        if not password:
                            sys.stderr.write('"admin" password is required.\n')
                            continue
                        break
                if not options.reset_password:
                    admin.password = password
            admin.save()
            if options.reset_password:
                User.reset_password([admin])
            if options.hostname is not None:
                configuration.hostname = options.hostname or None
            configuration.save()
