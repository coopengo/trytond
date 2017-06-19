# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from sql import Query, Expression, Literal, Column
from sql.aggregate import Max
from sql.conditionals import Coalesce
from sql.operators import Or

from .field import Field, SQLType
from ...pool import Pool
from ... import backend
from ...tools import reduce_ids
from ...transaction import Transaction


class Many2One(Field):
    '''
    Define many2one field (``int``).
    '''
    _type = 'many2one'

    def __init__(self, model_name, string='', left=None, right=None,
            ondelete='SET NULL', datetime_field=None, target_search='join',
            help='', required=False, readonly=False, domain=None, states=None,
            select=False, on_change=None, on_change_with=None, depends=None,
            context=None, loading='eager'):
        '''
        :param model_name: The name of the target model.
        :param left: The name of the field to store the left value for
            Modified Preorder Tree Traversal.
            See http://en.wikipedia.org/wiki/Tree_traversal
        :param right: The name of the field to store the right value. See left
        :param ondelete: Define the behavior of the record when the target
            record is deleted. (``CASCADE``, ``RESTRICT``, ``SET NULL``)
            ``SET NULL`` will be changed into ``RESTRICT`` if required is set.
        :param datetime_field: The name of the field that contains the datetime
            value to read the target record.
        :param target_search: The kind of target search 'subquery' or 'join'
        '''
        self.__required = required
        if ondelete not in ('CASCADE', 'RESTRICT', 'SET NULL'):
            raise Exception('Bad arguments')
        self.ondelete = ondelete
        if datetime_field:
            if depends:
                depends.append(datetime_field)
            else:
                depends = [datetime_field]
        super(Many2One, self).__init__(string=string, help=help,
            required=required, readonly=readonly, domain=domain, states=states,
            select=select, on_change=on_change, on_change_with=on_change_with,
            depends=depends, context=context, loading=loading)
        self.model_name = model_name
        self.left = left
        self.right = right
        self.datetime_field = datetime_field
        assert target_search in ['subquery', 'join']
        self.target_search = target_search
    __init__.__doc__ += Field.__init__.__doc__

    def __get_required(self):
        return self.__required

    def __set_required(self, value):
        self.__required = value
        if value and self.ondelete == 'SET NULL':
            self.ondelete = 'RESTRICT'

    required = property(__get_required, __set_required)

    def get_target(self):
        'Return the target Model'
        return Pool().get(self.model_name)

    def __set__(self, inst, value):
        Target = self.get_target()
        if isinstance(value, dict):
            value = Target(**value)
        elif isinstance(value, (int, long)):
            value = Target(value)
        assert isinstance(value, (Target, type(None)))
        super(Many2One, self).__set__(inst, value)

    @staticmethod
    def sql_format(value):
        if isinstance(value, (Query, Expression)):
            return value
        if value is None:
            return None
        assert value is not False
        return int(value)

    def sql_type(self):
        db_type = backend.name()
        if db_type == 'postgresql':
            return SQLType('INT4', 'INT4')
        elif db_type == 'mysql':
            return SQLType('SIGNED INTEGER', 'BIGINT')
        else:
            return SQLType('INTEGER', 'INTEGER')

    def convert_domain_mptt(self, domain, tables):
        cursor = Transaction().connection.cursor()
        table, _ = tables[None]
        name, operator, ids = domain
        red_sql = reduce_ids(table.id, ids)
        Target = self.get_target()
        left = getattr(Target, self.left).sql_column(table)
        right = getattr(Target, self.right).sql_column(table)
        cursor.execute(*table.select(left, right, where=red_sql))
        where = Or()
        for l, r in cursor.fetchall():
            if operator.endswith('child_of'):
                where.append((left >= l) & (right <= r))
            else:
                where.append((left <= l) & (right >= r))
        if not where:
            where = Literal(False)
        if operator.startswith('not'):
            return ~where
        return where

    def convert_domain_tree(self, domain, tables):
        Target = self.get_target()
        table, _ = tables[None]
        name, operator, ids = domain
        ids = set(ids)  # Ensure it is a set for concatenation

        def get_child(ids):
            if not ids:
                return set()
            children = Target.search([
                    (name, 'in', ids),
                    (name, '!=', None),
                    ], order=[])
            child_ids = get_child(set(c.id for c in children))
            return ids | child_ids

        def get_parent(ids):
            if not ids:
                return set()
            parent_ids = set(getattr(p, name).id
                for p in Target.browse(ids) if getattr(p, name))
            return ids | get_parent(parent_ids)

        if operator.endswith('child_of'):
            ids = list(get_child(ids))
        else:
            ids = list(get_parent(ids))
        if not ids:
            expression = Literal(False)
        else:
            expression = table.id.in_(ids)
        if operator.startswith('not'):
            return ~expression
        return expression

    def convert_domain(self, domain, tables, Model):
        pool = Pool()
        Rule = pool.get('ir.rule')
        Target = self.get_target()

        table, _ = tables[None]
        name, operator, value = domain[:3]
        column = self.sql_column(table)
        if '.' not in name:
            if operator.endswith('child_of') or operator.endswith('parent_of'):
                if Target != Model:
                    if operator.endswith('child_of'):
                        target_operator = 'child_of'
                    else:
                        target_operator = 'parent_of'
                    query = Target.search([
                            (domain[3], target_operator, value),
                            ], order=[], query=True)
                    expression = column.in_(query)
                    if operator.startswith('not'):
                        return ~expression
                    return expression

                if isinstance(value, basestring):
                    targets = Target.search([('rec_name', 'ilike', value)],
                        order=[])
                    ids = [t.id for t in targets]
                elif not isinstance(value, (list, tuple)):
                    ids = [value]
                else:
                    ids = value
                if not ids:
                    expression = Literal(False)
                    if operator.startswith('not'):
                        return ~expression
                    return expression
                elif self.left and self.right:
                    return self.convert_domain_mptt(
                        (name, operator, ids), tables)
                else:
                    return self.convert_domain_tree(
                        (name, operator, ids), tables)

            if not isinstance(value, basestring):
                return super(Many2One, self).convert_domain(domain, tables,
                    Model)
            else:
                target_name = 'rec_name'
        else:
            _, target_name = name.split('.', 1)
        target_domain = [(target_name,) + tuple(domain[1:])]
        if 'active' in Target._fields:
            target_domain.append(('active', 'in', [True, False]))
        if self.target_search == 'subquery':
            query = Target.search(target_domain, order=[], query=True)
            return column.in_(query)
        else:
            target_tables = self._get_target_tables(tables)
            target_table, _ = target_tables[None]
            rule_domain = Rule.domain_get(Target.__name__, mode='read')
            if rule_domain:
                target_domain = [target_domain, rule_domain]
            _, expression = Target.search_domain(
                target_domain, tables=target_tables)
            return expression

    def convert_order(self, name, tables, Model):
        fname, _, oexpr = name.partition('.')
        if not oexpr and getattr(Model, 'order_%s' % fname, None):
            return super(Many2One, self).convert_order(fname, tables, Model)
        assert fname == self.name

        Target = self.get_target()

        if oexpr:
            oname, _, _ = oexpr.partition('.')
        else:
            oname = 'id'
            if Target._rec_name in Target._fields:
                oname = Target._rec_name
            if Target._order_name in Target._fields:
                oname = Target._order_name
            oexpr = oname

        table, _ = tables[None]
        if oname == 'id':
            return [self.sql_column(table)]

        ofield = Target._fields[oname]
        target_tables = self._get_target_tables(tables)
        return ofield.convert_order(oexpr, target_tables, Target)

    def _get_target_tables(self, tables):
        Target = self.get_target()
        table, _ = tables[None]
        target_tables = tables.get(self.name)
        context = Transaction().context
        if target_tables is None:
            if Target._history and context.get('_datetime'):
                target = Target.__table_history__()
                target_history = Target.__table_history__()
                history_condition = Column(target, '__id').in_(
                    target_history.select(
                        Max(Column(target_history, '__id')),
                        where=Coalesce(
                            target_history.write_date,
                            target_history.create_date)
                        <= context['_datetime'],
                        group_by=target_history.id))
            else:
                target = Target.__table__()
                history_condition = None
            condition = target.id == self.sql_column(table)
            if history_condition:
                condition &= history_condition
            target_tables = {
                None: (target, condition),
                }
            tables[self.name] = target_tables
        return target_tables
