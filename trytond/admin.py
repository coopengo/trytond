# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys
import os
import logging
from getpass import getpass

from sql import Table

from trytond.transaction import Transaction
from trytond import backend
from trytond.pool import Pool
from trytond.config import config

from trytond.modules import get_module_info, get_module_list
from trytond.cache import Cache

__all__ = ['run']
logger = logging.getLogger(__name__)

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
    cursor.execute(*version_control_table.select(version_control_table.current_version, version_control_table.is_upgrading))
    db_main_module_version, is_upgrading = cursor.fetchone()

    # If the main module is upgrading, other upgradings are not allowed
    if is_upgrading:
        return False, current_main_module_version

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

        # Do the update only when it is needed
        with Transaction().start(db_name, 0) as transaction:
            cursor = transaction.connection.cursor()
            # Lock table to upgrade
            cursor.execute("LOCK upgrade_version_control IN EXCLUSIVE MODE;")
            is_upgrade_needed, new_version = _check_update_needed(db_name, options, transaction)
            if not is_upgrade_needed:
                options.update = []
                options.check_update = []
            pool.init(update=options.update or options.check_update, lang=list(lang), activatedeps=options.activatedeps)                
            if is_upgrade_needed:
                # If upgrade finishes correctly -> update version in database and reset is_upgrading to false
                try:
                    version_control_table = Table('upgrade_version_control')
                    cursor.execute(*version_control_table.update(
                        columns=[version_control_table.current_version, version_control_table.is_upgrading],
                        values=[new_version, False]))
                    transaction.commit()

                except:
                    transaction.rollback()
                    logger.info('Upgrade was interrupted!')
                    raise

            if options.update_modules_list:
                Module = pool.get('ir.module')
                Module.update_list()

            if lang:
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
