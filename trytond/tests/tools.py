# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from proteus import config as pconfig, Model, Wizard

from .test_tryton import restore_db_cache, backup_db_cache, drop_db, create_db

__all__ = ['activate_modules', 'set_user']


def activate_modules(modules):
    if isinstance(modules, basestring):
        modules = [modules]
    cache_name = '-'.join(modules)
    # JCA : restore_db_cache fails if the database already exists
    drop_db()
    if restore_db_cache(cache_name):
        return _get_config()
    create_db()
    cfg = _get_config()
    Module = Model.get('ir.module')
    records = Module.find([
            ('name', 'in', modules),
            ])
    assert len(records) == len(modules)
    Module.click(records, 'activate')
    Wizard('ir.module.activate_upgrade').execute('upgrade')

    backup_db_cache(cache_name)
    return cfg


def _get_config():
    cfg = pconfig.set_trytond()
    cfg.pool.test = True
    return cfg


def set_user(user, config=None):
    if not config:
        config = pconfig.get_config()
    User = Model.get('res.user', config=config)
    config.user = int(user)
    config._context = User.get_preferences(True, {})
