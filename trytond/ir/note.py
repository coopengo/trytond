from textwrap import TextWrapper

from sql import Null
from sql.conditionals import Case

from ..model import ModelView, ModelSQL, fields
from ..pool import Pool
from ..transaction import Transaction
from ..tools import grouped_slice, reduce_ids
from ..pyson import If, Eval
from .resource import ResourceMixin

__all__ = ['Note', 'NoteRead']


class Note(ResourceMixin, ModelSQL, ModelView):
    "Note"
    __name__ = 'ir.note'
    message = fields.Text('Message', states={
            'readonly': Eval('id', 0) > 0,
            })
    message_wrapped = fields.Function(fields.Text('Message'),
        'on_change_with_message_wrapped')
    unread = fields.Function(fields.Boolean('Unread'), 'get_unread',
        searcher='search_unread', setter='set_unread')
    create_user = fields.Function(
        fields.Char('User', readonly=True),
        'get_create_user')
    creation_date = fields.Function(
        fields.DateTime('Creation Date', readonly=True),
        'get_creation_date')

    @staticmethod
    def default_unread():
        return False

    @classmethod
    def get_wrapper(cls):
        return TextWrapper(width=79)

    def get_create_user(self, name):
        return self.create_uid.rec_name

    def get_creation_date(self, name):
        return self.create_date.replace(microsecond=0)

    @fields.depends('message')
    def on_change_with_message_wrapped(self, name=None):
        wrapper = self.get_wrapper()
        return '\n'.join(map(wrapper.fill, self.message.splitlines()))

    @classmethod
    def get_unread(cls, ids, name):
        pool = Pool()
        Read = pool.get('ir.note.read')
        cursor = Transaction().cursor
        user_id = Transaction().user
        table = cls.__table__()
        read = Read.__table__()

        unread = {}
        for sub_ids in grouped_slice(ids):
            where = reduce_ids(table.id, sub_ids)
            query = table.join(read, 'LEFT',
                condition=(table.id == read.note)
                & (read.user == user_id)
                ).select(table.id,
                    Case((read.user != Null, False), else_=True),
                    where=where)
            cursor.execute(*query)
            unread.update(cursor.fetchall())
        return unread

    @classmethod
    def search_unread(cls, name, clause):
        pool = Pool()
        Read = pool.get('ir.note.read')
        user_id = Transaction().user
        table = cls.__table__()
        read = Read.__table__()

        _, operator, value = clause
        assert operator in ['=', '!=']
        Operator = fields.SQL_OPERATORS[operator]

        where = Operator(Case((read.user != Null, False), else_=True), value)
        query = table.join(read, 'LEFT',
            condition=(table.id == read.note)
            & (read.user == user_id)
            ).select(table.id, where=where)
        return [('id', 'in', query)]

    @classmethod
    def set_unread(cls, notes, name, value):
        pool = Pool()
        Read = pool.get('ir.note.read')
        user_id = Transaction().user
        if not value:
            Read.create([{'note': n.id, 'user': user_id} for n in notes])
        else:
            reads = []
            for sub_notes in grouped_slice(notes):
                reads += Read.search([
                        ('note', 'in', [n.id for n in sub_notes]),
                        ('user', '=', user_id),
                        ])
            Read.delete(reads)

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors', If(Eval('unread', True), 'black', 'grey'))]


class NoteRead(ModelSQL):
    "Note Read"
    __name__ = 'ir.note.read'
    note = fields.Many2One('ir.note', 'Note', required=True,
        ondelete='CASCADE')
    user = fields.Many2One('res.user', 'User', required=True,
        ondelete='CASCADE')
