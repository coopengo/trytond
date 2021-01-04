from ..model import ModelSQL, ModelView, fields, Unique
from ..config import config

class ConfigParameter(ModelSQL, ModelView):
    "Configuration parameter"
    __name__ = "res.config.parameter"

    name = fields.Char('Name', required=True, select=True, translate=True)
    value = fields.Text('Value')
    section = fields.Many2One('res.config.section', 'Section', required=True)

    @classmethod
    def __setup__(cls):
        super(ConfigParameter, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('parameters_key', Unique(table, table.name, table.section),
                "You can only have once this parameter for this section")
        ]


class ConfigSection(ModelSQL):
    "Configuration section"
    __name__ = "res.config.section"
    name = fields.Char('Name', required=True, select=True, translate=True)
    parameters = fields.One2Many('res.config.parameter', 'section', 'Parameters')


class ConfigSectionView(ModelView):
    "Configuration viewer"
    __name__ = "res.config.section.view"

    section = fields.Selection('get_available_config', 'Config viewer',
        help="Determine which section you want to read")
    section_logs = fields.Text('get_section_description', depends=['section'])

    @classmethod
    def get_available_config(cls, name):
        configs = [('all', 'All')]
        configs += [(x, x) for x in config.sections()]
        return configs

    @fields.depends('section')
    def get_section_description(self):
        if self.section == 'all':
            return 'ALL'
        return 'Section'
