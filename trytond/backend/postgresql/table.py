# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import re
import logging

from psycopg2.sql import SQL, Identifier, Composed

from trytond.transaction import Transaction
from trytond.backend.table import TableHandlerInterface

__all__ = ['TableHandler']

logger = logging.getLogger(__name__)
VARCHAR_SIZE_RE = re.compile(r'VARCHAR\(([0-9]+)\)')


class TableHandler(TableHandlerInterface):
    namedatalen = 64

    def __init__(self, model, module_name=None, history=False):
        super(TableHandler, self).__init__(model,
                module_name=module_name, history=history)
        self._columns = {}
        self._constraints = []
        self._fk_deltypes = {}
        self._indexes = []

        transaction = Transaction()
        cursor = transaction.connection.cursor()
        # Create sequence if necessary
        if not transaction.database.sequence_exist(
                transaction.connection, self.sequence_name):
            transaction.database.sequence_create(
                transaction.connection, self.sequence_name)

        # Create new table if necessary
        if not self.table_exist(self.table_name):
            cursor.execute(SQL('CREATE TABLE {} ()').format(
                    Identifier(self.table_name)))
        self.table_schema = transaction.database.get_table_schema(
            transaction.connection, self.table_name)

        cursor.execute('SELECT tableowner = current_user FROM pg_tables '
            'WHERE tablename = %s AND schemaname = %s',
            (self.table_name, self.table_schema))
        self.is_owner, = cursor.fetchone()

        if model.__doc__ and self.is_owner:
            cursor.execute(SQL('COMMENT ON TABLE {} IS %s').format(
                        Identifier(self.table_name)),
                (model.__doc__,))

        self._update_definitions(columns=True)
        if 'id' not in self._columns:
            if not self.history:
                cursor.execute(
                    SQL(
                        "ALTER TABLE {} ADD COLUMN id INTEGER "
                        "DEFAULT nextval(%s) NOT NULL").format(
                        Identifier(self.table_name)),
                    (self.sequence_name,))
                cursor.execute(
                    SQL('ALTER TABLE {} ADD PRIMARY KEY(id)')
                    .format(Identifier(self.table_name)))
            else:
                cursor.execute(
                    SQL('ALTER TABLE {} ADD COLUMN id INTEGER')
                    .format(Identifier(self.table_name)))
            self._update_definitions(columns=True)
        if self.history and '__id' not in self._columns:
            cursor.execute(
                SQL(
                    "ALTER TABLE {} ADD COLUMN __id INTEGER "
                    "DEFAULT nextval('{}') NOT NULL").format(
                        Identifier(self.table_name),
                        Identifier(self.sequence_name)))
            cursor.execute(
                SQL('ALTER TABLE {} ADD PRIMARY KEY(__id)')
                .format(Identifier(self.table_name)))
        else:
            default = "nextval('%s'::regclass)" % self.sequence_name
            if self.history:
                if self._columns['__id']['default'] != default:
                    cursor.execute(
                        SQL("ALTER TABLE {} "
                            "ALTER __id SET DEFAULT nextval(%s::regclass)")
                        .format(Identifier(self.table_name)),
                        (self.sequence_name,))
            if self._columns['id']['default'] != default:
                cursor.execute(
                    SQL("ALTER TABLE {} "
                        "ALTER id SET DEFAULT nextval(%s::regclass)")
                    .format(Identifier(self.table_name)),
                    (self.sequence_name,))
        self._update_definitions()

    @staticmethod
    def table_exist(table_name):
        transaction = Transaction()
        return bool(transaction.database.get_table_schema(
                transaction.connection, table_name))

    @staticmethod
    def table_rename(old_name, new_name):
        transaction = Transaction()
        cursor = transaction.connection.cursor()
        # Rename table
        if (TableHandler.table_exist(old_name)
                and not TableHandler.table_exist(new_name)):
            cursor.execute(SQL('ALTER TABLE {} RENAME TO {}').format(
                    Identifier(old_name), Identifier(new_name)))
        # Rename sequence
        old_sequence = old_name + '_id_seq'
        new_sequence = new_name + '_id_seq'
        transaction.database.sequence_rename(
            transaction.connection, old_sequence, new_sequence)
        # Rename history table
        old_history = old_name + "__history"
        new_history = new_name + "__history"
        if (TableHandler.table_exist(old_history)
                and not TableHandler.table_exist(new_history)):
            cursor.execute('ALTER TABLE "%s" RENAME TO "%s"'
                % (old_history, new_history))

    def column_exist(self, column_name):
        return column_name in self._columns

    def column_rename(self, old_name, new_name):
        cursor = Transaction().connection.cursor()
        if self.column_exist(old_name):
            if not self.column_exist(new_name):
                cursor.execute(SQL(
                        'ALTER TABLE {} RENAME COLUMN {} TO {}').format(
                        Identifier(self.table_name),
                        Identifier(old_name),
                        Identifier(new_name)))
                self._update_definitions(columns=True)
            else:
                logger.warning(
                    'Unable to rename column %s on table %s to %s.',
                    old_name, self.table_name, new_name)

    def _update_definitions(self,
            columns=None, constraints=None, indexes=None):
        if columns is None and constraints is None and indexes is None:
            columns = constraints = indexes = True
        cursor = Transaction().connection.cursor()
        if columns:
            self._columns = {}
            # Fetch columns definitions from the table
            cursor.execute('SELECT '
                'column_name, udt_name, is_nullable, '
                'character_maximum_length, '
                'column_default '
                'FROM information_schema.columns '
                'WHERE table_name = %s AND table_schema = %s',
                (self.table_name, self.table_schema))
            for column, typname, nullable, size, default in cursor.fetchall():
                self._columns[column] = {
                    'typname': typname,
                    'notnull': True if nullable == 'NO' else False,
                    'size': size,
                    'default': default,
                    }

        if constraints:
            # fetch constraints for the table
            cursor.execute('SELECT constraint_name '
                'FROM information_schema.table_constraints '
                'WHERE table_name = %s AND table_schema = %s',
                (self.table_name, self.table_schema))
            self._constraints = [c for c, in cursor.fetchall()]

            # add nonstandard exclude constraint
            cursor.execute('SELECT c.conname '
                'FROM pg_namespace nc, '
                    'pg_namespace nr, '
                    'pg_constraint c, '
                    'pg_class r '
                'WHERE nc.oid = c.connamespace AND nr.oid = r.relnamespace '
                    'AND c.conrelid = r.oid '
                    "AND c.contype = 'x' "  # exclude type
                    "AND r.relkind IN ('r', 'p') "
                    'AND r.relname = %s AND nr.nspname = %s',
                    (self.table_name, self.table_schema))
            self._constraints.extend((c for c, in cursor.fetchall()))

            cursor.execute('SELECT k.column_name, r.delete_rule '
                'FROM information_schema.key_column_usage AS k '
                'JOIN information_schema.referential_constraints AS r '
                'ON r.constraint_schema = k.constraint_schema '
                'AND r.constraint_name = k.constraint_name '
                'WHERE k.table_name = %s AND k.table_schema = %s',
                (self.table_name, self.table_schema))
            self._fk_deltypes = dict(cursor.fetchall())

        if indexes:
            # Fetch indexes defined for the table
            cursor.execute("SELECT cl2.relname "
                "FROM pg_index ind "
                    "JOIN pg_class cl on (cl.oid = ind.indrelid) "
                    "JOIN pg_namespace n ON (cl.relnamespace = n.oid) "
                    "JOIN pg_class cl2 on (cl2.oid = ind.indexrelid) "
                "WHERE cl.relname = %s AND n.nspname = %s",
                (self.table_name, self.table_schema))
            self._indexes = [l[0] for l in cursor.fetchall()]

    @property
    def _field2module(self):
        cursor = Transaction().connection.cursor()
        cursor.execute('SELECT f.name, f.module '
            'FROM ir_model_field f '
                'JOIN ir_model m on (f.model=m.id) '
            'WHERE m.model = %s',
            (self.object_name,))
        return dict(cursor)

    def alter_size(self, column_name, column_type):
        cursor = Transaction().connection.cursor()
        cursor.execute(
            SQL(
                "ALTER TABLE {} RENAME COLUMN {} TO _temp_change_size").format(
                Identifier(self.table_name),
                Identifier(column_name)))
        cursor.execute(SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                Identifier(self.table_name),
                Identifier(column_name),
                SQL(column_type)))
        cursor.execute(
            SQL("UPDATE {} SET {} = _temp_change_size::%s").format(
                Identifier(self.table_name),
                Identifier(column_name),
                SQL(column_type)))
        cursor.execute(
            SQL("ALTER TABLE {} " "DROP COLUMN _temp_change_size")
            .format(Identifier(self.table_name)))
        self._update_definitions(columns=True)

    def alter_type(self, column_name, column_type):
        cursor = Transaction().connection.cursor()
        cursor.execute(SQL('ALTER TABLE {} ALTER {} TYPE {}').format(
                Identifier(self.table_name),
                Identifier(column_name),
                SQL(column_type)))
        self._update_definitions(columns=True)

    def column_is_type(self, column_name, type_, *, size=-1):
        db_type = self._columns[column_name]['typname'].upper()

        database = Transaction().database
        base_type = database.sql_type(type_).base.upper()
        if base_type == 'VARCHAR' and (size is None or size >= 0):
            same_size = self._columns[column_name]['size'] == size
        else:
            same_size = True

        return base_type == db_type and same_size

    def db_default(self, column_name, value):
        if value in [True, False]:
            test = str(value).lower()
        else:
            test = value
        if self._columns[column_name]['default'] != test:
            cursor = Transaction().connection.cursor()
            cursor.execute(
                SQL(
                    'ALTER TABLE {} ALTER COLUMN {} SET DEFAULT %s').format(
                    Identifier(self.table_name),
                    Identifier(column_name)),
                (value,))

    def add_column(self, column_name, sql_type, default=None, comment=''):
        cursor = Transaction().connection.cursor()
        database = Transaction().database

        column_type = database.sql_type(sql_type)
        match = VARCHAR_SIZE_RE.match(sql_type)
        field_size = int(match.group(1)) if match else None

        def add_comment():
            if comment and self.is_owner:
                cursor.execute(
                    SQL('COMMENT ON COLUMN {}.{} IS %s').format(
                        Identifier(self.table_name),
                        Identifier(column_name)),
                    (comment,))
        if self.column_exist(column_name):
            if (column_name in ('create_date', 'write_date')
                    and column_type[1].lower() != 'timestamp(6)'):
                # Migrate dates from timestamp(0) to timestamp
                cursor.execute(
                    SQL(
                        'ALTER TABLE {} ALTER COLUMN {} TYPE timestamp')
                    .format(
                        Identifier(self.table_name),
                        Identifier(column_name)))

            add_comment()
            base_type = column_type[0].lower()
            if base_type != self._columns[column_name]['typname']:
                if (self._columns[column_name]['typname'], base_type) in [
                        ('varchar', 'text'),
                        ('text', 'varchar'),
                        ('date', 'timestamp'),
                        ('int4', 'float8'),
                        ]:
                    self.alter_type(column_name, base_type)
                else:
                    logger.warning(
                        'Unable to migrate column %s on table %s '
                        'from %s to %s.',
                        column_name, self.table_name,
                        self._columns[column_name]['typname'], base_type)

            if (base_type == 'varchar'
                    and self._columns[column_name]['typname'] == 'varchar'):
                # Migrate size
                from_size = self._columns[column_name]['size']
                if field_size is None:
                    if from_size:
                        self.alter_size(column_name, base_type)
                elif from_size == field_size:
                    pass
                elif from_size and from_size < field_size:
                    self.alter_size(column_name, column_type[1])
                else:
                    logger.warning(
                        'Unable to migrate column %s on table %s '
                        'from varchar(%s) to varchar(%s).',
                        column_name, self.table_name,
                        from_size if from_size and from_size > 0 else "",
                        field_size)
            return

        column_type = column_type[1]
        cursor.execute(
            SQL('ALTER TABLE {} ADD COLUMN {} {}').format(
                Identifier(self.table_name),
                Identifier(column_name),
                SQL(column_type)))
        add_comment()

        if default:
            # check if table is non-empty:
            cursor.execute('SELECT 1 FROM "%s" limit 1' % self.table_name)
            if cursor.rowcount:
                # Populate column with default values:
                cursor.execute(
                    SQL('UPDATE {} SET {} = %s').format(
                        Identifier(self.table_name),
                        Identifier(column_name)),
                    (default(),))

        self._update_definitions(columns=True)

    def add_fk(self, column_name, reference, on_delete=None):
        if on_delete is not None:
            on_delete = on_delete.upper()
        else:
            on_delete = 'SET NULL'

        cursor = Transaction().connection.cursor()
        name = self.convert_name(self.table_name + '_' + column_name + '_fkey')
        if name in self._constraints:
            if self._fk_deltypes.get(column_name) != on_delete:
                self.drop_fk(column_name)
                add = True
            else:
                add = False
        else:
            add = True
        if add:
            cursor.execute(
                SQL(
                    "ALTER TABLE {table} "
                    "ADD CONSTRAINT {constraint} "
                    "FOREIGN KEY ({column}) REFERENCES {reference} "
                    "ON DELETE {action}"
                    )
                .format(
                    table=Identifier(self.table_name),
                    constraint=Identifier(name),
                    column=Identifier(column_name),
                    reference=Identifier(reference),
                    action=SQL(on_delete)))
        self._update_definitions(constraints=True)

    def drop_fk(self, column_name, table=None):
        self.drop_constraint(column_name + '_fkey', table=table)

    def index_action(self, columns, action='add', where='', table=None):
        if isinstance(columns, str):
            columns = [columns]

        def stringify(column):
            if isinstance(column, str):
                return column
            else:
                return ('_'.join(
                        map(str, (column,) + column.params))
                    .replace('"', '')
                    .replace('%s', '__'))

        name = [table or self.table_name]
        name.append('_'.join(map(stringify, columns)))
        if where:
            name.append('+where')
            name.append(stringify(where))
        name.append('index')
        index_name = self.convert_name('_'.join(name))

        with Transaction().connection.cursor() as cursor:
            if action == 'add':
                if index_name in self._indexes:
                    return
                columns_quoted = []
                for column in columns:
                    if isinstance(column, str):
                        columns_quoted.append(Identifier(column))
                    else:
                        columns_quoted.append(SQL(str(column)))
                params = sum(
                    (c.params for c in columns if hasattr(c, 'params')), ())
                if where:
                    params += where.params
                    where = ' WHERE %s' % where
                cursor.execute(Composed([
                            SQL('CREATE INDEX {name} ON {table} ({columns})')
                            .format(
                                name=Identifier(index_name),
                                table=Identifier(self.table_name),
                                columns=SQL(',').join(columns_quoted)),
                            SQL(where)
                            ]),
                    params)
                self._update_definitions(indexes=True)
            elif action == 'remove':
                if len(columns) == 1 and isinstance(columns[0], str):
                    if self._field2module.get(columns[0],
                            self.module_name) != self.module_name:
                        return

                if index_name in self._indexes:
                    cursor.execute(SQL('DROP INDEX {}').format(
                            Identifier(index_name)))
                    self._update_definitions(indexes=True)
            else:
                raise Exception('Index action not supported!')

    def not_null_action(self, column_name, action='add'):
        if not self.column_exist(column_name):
            return

        with Transaction().connection.cursor() as cursor:
            if action == 'add':
                if self._columns[column_name]['notnull']:
                    return
                cursor.execute(SQL(
                        'SELECT id FROM {} WHERE {} IS NULL').format(
                        Identifier(self.table_name),
                        Identifier(column_name)))
                if not cursor.rowcount:
                    cursor.execute(
                        SQL(
                            'ALTER TABLE {} ALTER COLUMN {} SET NOT NULL')
                        .format(
                            Identifier(self.table_name),
                            Identifier(column_name)))
                    self._update_definitions(columns=True)
                else:
                    logger.warning(
                        'Unable to set column %s '
                        'of table %s not null !\n'
                        'Try to re-run: '
                        'trytond.py --update=module\n'
                        'If it doesn\'t work, update records '
                        'and execute manually:\n'
                        'ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL',
                        column_name, self.table_name, self.table_name,
                        column_name)
            elif action == 'remove':
                if not self._columns[column_name]['notnull']:
                    return
                if (self._field2module.get(column_name, self.module_name)
                        != self.module_name):
                    return
                cursor.execute(
                    SQL('ALTER TABLE {} ALTER COLUMN {} DROP NOT NULL')
                    .format(
                        Identifier(self.table_name),
                        Identifier(column_name)))
                self._update_definitions(columns=True)
            else:
                raise Exception('Not null action not supported!')

    def add_constraint(self, ident, constraint):
        ident = self.convert_name(self.table_name + "_" + ident)
        if ident in self._constraints:
            # This constrain already exist
            return
        cursor = Transaction().connection.cursor()
        cursor.execute(
            SQL('ALTER TABLE {} ADD CONSTRAINT {} {}').format(
                Identifier(self.table_name),
                Identifier(ident),
                SQL(str(constraint))),
            constraint.params)
        self._update_definitions(constraints=True)

    def drop_constraint(self, ident, table=None):
        ident = self.convert_name((table or self.table_name) + "_" + ident)
        if ident not in self._constraints:
            return
        cursor = Transaction().connection.cursor()
        cursor.execute(
            SQL('ALTER TABLE {} DROP CONSTRAINT {}').format(
                Identifier(self.table_name), Identifier(ident)))
        self._update_definitions(constraints=True)

    def drop_column(self, column_name):
        if not self.column_exist(column_name):
            return
        cursor = Transaction().connection.cursor()
        cursor.execute(SQL('ALTER TABLE {} DROP COLUMN {}').format(
                Identifier(self.table_name),
                Identifier(column_name)))
        self._update_definitions(columns=True)

    @staticmethod
    def drop_table(model, table, cascade=False):
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM ir_model_data WHERE model = %s', (model,))

        query = 'DROP TABLE {}'
        if cascade:
            query = query + ' CASCADE'
        cursor.execute(SQL(query).format(Identifier(table)))
