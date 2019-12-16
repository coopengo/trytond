# This file is part of Tryton.  The COPYRIGHT file at the toplevel of this
# repository contains the full copyright notices and license terms.
import json
from collections import OrderedDict

from trytond.i18n import gettext
from trytond.model import fields
from trytond.model.exceptions import ValidationError
from trytond.pyson import Eval, PYSONDecoder
from trytond.rpc import RPC
from trytond.transaction import Transaction
from trytond.pool import Pool


class DomainError(ValidationError):
    pass


class SelectionError(ValidationError):
    pass


class DictSchemaMixin(object):
    _rec_name = 'string'
    name = fields.Char('Name', required=True)
    string = fields.Char('String', translate=True, required=True)
    help = fields.Text(
        "Help",
        translate=True)
    type_ = fields.Selection([
            ('boolean', 'Boolean'),
            ('integer', 'Integer'),
            ('char', 'Char'),
            ('float', 'Float'),
            ('numeric', 'Numeric'),
            ('date', 'Date'),
            ('datetime', 'DateTime'),
            ('selection', 'Selection'),
            ('multiselection', 'Multi-Selection'),
            ], 'Type', required=True)
    digits = fields.Integer('Digits', states={
            'invisible': ~Eval('type_').in_(['float', 'numeric']),
            }, depends=['type_'])
    domain = fields.Char("Domain")
    selection = fields.Text('Selection', states={
            'invisible': ~Eval('type_').in_(['selection', 'multiselection']),
            }, translate=True, depends=['type_'],
        help='A couple of key and label separated by ":" per line')
    selection_sorted = fields.Boolean('Selection Sorted', states={
            'invisible': ~Eval('type_').in_(['selection', 'multiselection']),
            }, depends=['type_'],
        help='If the selection must be sorted on label')
    selection_json = fields.Function(fields.Char('Selection JSON',
            states={
                'invisible': ~Eval('type_').in_(
                    ['selection', 'multiselection']),
                },
            depends=['type_']), 'get_selection_json')

    @classmethod
    def __setup__(cls):
        super(DictSchemaMixin, cls).__setup__()
        cls.__rpc__.update({
                'get_keys': RPC(instantiate=0),
                })

    @staticmethod
    def default_digits():
        return 2

    @staticmethod
    def default_selection_sorted():
        return True

    @classmethod
    def validate(cls, schemas):
        super(DictSchemaMixin, cls).validate(schemas)
        cls.check_domain(schemas)
        cls.check_selection(schemas)

    @classmethod
    def check_domain(cls, schemas):
        for schema in schemas:
            if not schema.domain:
                continue
            try:
                value = PYSONDecoder().decode(schema.domain)
            except Exception:
                raise DomainError(
                    gettext('ir.msg_dict_schema_invalid_domain',
                        schema=schema.rec_name))
            if not isinstance(value, list):
                raise DomainError(
                    gettext('ir.msg_dict_schema_invalid_domain',
                        schema=schema.rec_name))

    @classmethod
    def check_selection(cls, schemas):
        for schema in schemas:
            if schema.type_ not in {'selection', 'multiselection'}:
                continue
            try:
                dict(json.loads(schema.get_selection_json()))
            except Exception:
                raise SelectionError(
                    gettext('ir.msg_dict_schema_invalid_selection',
                        schema=schema.rec_name))

    def get_selection_json(self, name=None):
        db_selection = self.selection or ''
        selection = [[w.strip() for w in v.split(':', 1)]
            for v in db_selection.splitlines() if v]
        return json.dumps(selection, separators=(',', ':'))

    @classmethod
    def get_keys(cls, records):
        pool = Pool()
        Config = pool.get('ir.configuration')
        keys = []
        for record in records:
            new_key = {
                'id': record.id,
                'name': record.name,
                'string': record.string,
                'help': record.help,
                'type_': record.type_,
                'domain': record.domain,
                }
            if record.type_ in {'selection', 'multiselection'}:
                with Transaction().set_context(language=Config.get_language()):
                    english_key = cls(record.id)
                    selection = OrderedDict(json.loads(
                            english_key.selection_json))
                selection.update(dict(json.loads(record.selection_json)))
                new_key['selection'] = list(selection.items())
                new_key['sorted'] = record.selection_sorted
            elif record.type_ in ('float', 'numeric'):
                new_key['digits'] = (16, record.digits)
            # ABDC Inject sequence order in dict schema to allow client sorting
            # properly using this custom sequence instead of extra data key
            if hasattr(record, 'sequence_order'):
                new_key['sequence_order'] = record.sequence_order
            keys.append(new_key)
        return keys
