# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import time
import datetime
import os
import inspect
import logging
import subprocess
import tempfile
import time
import warnings
import zipfile
import requests
import operator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

try:
    import html2text
except ImportError:
    html2text = None

try:
    import weasyprint
except ImportError:
    weasyprint = None

from genshi.filters import Translator

from trytond.i18n import gettext
from trytond.pool import Pool, PoolBase
from trytond.transaction import Transaction
from trytond.config import config
from trytond.tools import slugify
from trytond.url import URLMixin
from trytond.rpc import RPC
from trytond.exceptions import UserError

warnings.simplefilter("ignore")
import relatorio.reporting  # noqa: E402
warnings.resetwarnings()
try:
    from relatorio.templates.opendocument import Manifest, MANIFEST
except ImportError:
    Manifest, MANIFEST = None, None

logger = logging.getLogger(__name__)


MIMETYPES = {
    'odt': 'application/vnd.oasis.opendocument.text',
    'odp': 'application/vnd.oasis.opendocument.presentation',
    'ods': 'application/vnd.oasis.opendocument.spreadsheet',
    'odg': 'application/vnd.oasis.opendocument.graphics',
    'txt': 'text/plain',
    'xml': 'text/xml',
    'html': 'text/html',
    'xhtml': 'text/xhtml',
    }
FORMAT2EXT = {
    'doc6': 'doc',
    'doc95': 'doc',
    'docbook': 'xml',
    'docx7': 'docx',
    'docx': 'docx',
    'ooxml': 'xml',
    'latex': 'ltx',
    'sdc4': 'sdc',
    'sdc3': 'sdc',
    'sdd3': 'sdd',
    'sdd4': 'sdd',
    'sdw4': 'sdw',
    'sdw3': 'sdw',
    'sxd3': 'sxd',
    'sxd5': 'sxd',
    'text': 'txt',
    'xhtml': 'html',
    'xls5': 'xls',
    'xls95': 'xls',
    'xlsx': 'xlsx',
    }

TIMEDELTA_DEFAULT_CONVERTER = {
    's': 1,
    }
TIMEDELTA_DEFAULT_CONVERTER['m'] = TIMEDELTA_DEFAULT_CONVERTER['s'] * 60
TIMEDELTA_DEFAULT_CONVERTER['h'] = TIMEDELTA_DEFAULT_CONVERTER['m'] * 60
TIMEDELTA_DEFAULT_CONVERTER['d'] = TIMEDELTA_DEFAULT_CONVERTER['h'] * 24
TIMEDELTA_DEFAULT_CONVERTER['w'] = TIMEDELTA_DEFAULT_CONVERTER['d'] * 7
TIMEDELTA_DEFAULT_CONVERTER['M'] = TIMEDELTA_DEFAULT_CONVERTER['d'] * 30
TIMEDELTA_DEFAULT_CONVERTER['Y'] = TIMEDELTA_DEFAULT_CONVERTER['d'] * 365


class UnoConversionError(UserError):
    pass


class ReportFactory:

    def __call__(self, records, **kwargs):
        data = {}
        data['objects'] = records  # XXX To remove
        data['records'] = records
        data.update(kwargs)
        return data


class TranslateFactory:

    def __init__(self, report_name, language, translation):
        self.report_name = report_name
        self.language = language
        self.translation = translation
        self.cache = {}

    def __call__(self, text):
        from trytond.ir.lang import get_parent_language
        if self.language not in self.cache:
            cache = self.cache[self.language] = {}
            code = self.language
            while code:
                # Order to get empty module/custom report first
                translations = self.translation.search([
                    ('lang', '=', code),
                    ('type', '=', 'report'),
                    ('name', '=', self.report_name),
                    ('value', '!=', ''),
                    ('value', '!=', None),
                    ('fuzzy', '=', False),
                    ('res_id', '=', -1),
                    ], order=[('module', 'DESC')])
                for translation in translations:
                    cache.setdefault(translation.src, translation.value)
                code = get_parent_language(code)
        return self.cache[self.language].get(text, text)

    def set_language(self, language=None):
        pool = Pool()
        Config = pool.get('ir.configuration')
        Lang = pool.get('ir.lang')
        if isinstance(language, Lang):
            language = language.code
        if not language:
            language = Config.get_language()
        self.language = language


class Report(URLMixin, PoolBase):

    @classmethod
    def __setup__(cls):
        super(Report, cls).__setup__()
        cls.__rpc__ = {
            'execute': RPC(),
            }

    @classmethod
    def check_access(cls):
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        User = pool.get('res.user')

        if Transaction().user == 0:
            return

        groups = set(User.get_groups())
        report_groups = ActionReport.get_groups(cls.__name__)
        if report_groups and not groups & report_groups:
            raise UserError('Calling report %s is not allowed!' % cls.__name__)

    @classmethod
    def execute(cls, ids, data):
        '''
        Execute the report on record ids.
        The dictionary with data that will be set in local context of the
        report.
        It returns a tuple with:
            report type,
            data,
            a boolean to direct print,
            the report name
        '''
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        cls.check_access()

        action_id = data.get('action_id')
        if action_id is None:
            action_reports = ActionReport.search([
                    ('report_name', '=', cls.__name__)
                    ])
            assert action_reports, '%s not found' % cls
            action_report = action_reports[0]
        else:
            action_report = ActionReport(action_id)

        records = []
        model = action_report.model or data.get('model')
        if model:
            records = cls._get_records(ids, model, data)
        if action_report.single and len(records) > 1:
            content = BytesIO()
            with zipfile.ZipFile(content, 'w') as content_zip:
                for record in records:
                    oext, rcontent = cls._execute(
                        [record], data, action_report)
                    filename = slugify('%s-%s' % (record.id, record.rec_name))
                    rfilename = '%s.%s' % (filename, oext)
                    content_zip.writestr(rfilename, rcontent)
            content = content.getvalue()
            oext = 'zip'
        else:
            oext, content = cls._execute(records, data, action_report)
        if not isinstance(content, str):
            content = bytearray(content) if bytes == str else bytes(content)
        return (oext, content, action_report.direct_print, action_report.name)

    @classmethod
    def _execute(cls, records, data, action):
        report_context = cls.get_context(records, data)
        return cls.convert(action, cls.render(action, report_context))

    @classmethod
    def _get_records(cls, ids, model, data):
        pool = Pool()
        Model = pool.get(model)
        Config = pool.get('ir.configuration')
        Lang = pool.get('ir.lang')
        context = Transaction().context

        class TranslateModel(object):
            _languages = {}

            def __init__(self, id):
                self.id = id
                self._language = Transaction().language

            def set_lang(self, language=None):
                if isinstance(language, Lang):
                    language = language.code
                if not language:
                    language = Config.get_language()
                self._language = language

            def __getattr__(self, name):
                if self._language not in TranslateModel._languages:
                    with Transaction().set_context(
                            context=context, language=self._language):
                        records = Model.browse(ids)
                    id2record = dict((r.id, r) for r in records)
                    TranslateModel._languages[self._language] = id2record
                else:
                    id2record = TranslateModel._languages[self._language]
                record = id2record[self.id]
                return getattr(record, name)

            def __int__(self):
                return int(self.id)

            def __str__(self):
                return '%s,%s' % (Model.__name__, self.id)

        return [TranslateModel(id) for id in ids]

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        User = pool.get('res.user')

        report_context = {}
        report_context['data'] = data
        report_context['context'] = Transaction().context
        report_context['user'] = User(Transaction().user)
        report_context['records'] = records
        report_context['record'] = records[0] if records else None
        report_context['format_date'] = cls.format_date
        report_context['format_timedelta'] = cls.format_timedelta
        report_context['format_currency'] = cls.format_currency
        report_context['format_number'] = cls.format_number
        report_context['datetime'] = datetime

        return report_context

    @classmethod
    def _prepare_template_file(cls, report):
        # Convert to str as value from DB is not supported by StringIO
        report_content = (bytes(report.report_content) if report.report_content
            else None)
        if not report_content:
            raise Exception('Error', 'Missing report file!')

        fd, path = tempfile.mkstemp(
            suffix=(os.extsep + report.template_extension),
            prefix='trytond_')
        with open(path, 'wb') as f:
            f.write(report_content)
        return fd, path

    @classmethod
    def _add_translation_hook(cls, relatorio_report, context):
        pool = Pool()
        Translation = pool.get('ir.translation')

        translate = TranslateFactory(cls.__name__, Transaction().language,
            Translation)
        context['set_lang'] = lambda language: translate.set_language(language)
        translator = Translator(lambda text: translate(text))
        relatorio_report.filters.insert(0, translator)

    @classmethod
    def render(cls, report, report_context):
        "calls the underlying templating engine to renders the report"
        fd, path = cls._prepare_template_file(report)

        mimetype = MIMETYPES[report.template_extension]
        rel_report = relatorio.reporting.Report(path, mimetype,
                ReportFactory(), relatorio.reporting.MIMETemplateLoader())
        if report.translatable:
            cls._add_translation_hook(rel_report, report_context)
        else:
            report_context['set_lang'] = lambda language: None

        data = rel_report(**report_context).render()
        if hasattr(data, 'getvalue'):
            data = data.getvalue()
        os.close(fd)
        os.remove(path)

        return data

    @classmethod
    def convert(cls, report, data, timeout=5 * 60, retry=5):
        "converts the report data to another mimetype if necessary"
        # AKE: support printing via external api
        if config.get('report', 'api', default=None):
            return cls.convert_api(report, data, timeout)
        elif config.get('report', 'unoconv', default=True):
            return cls.convert_unoconv(report, data, timeout)
        else:
            raise NotImplementedError

    @classmethod
    def convert_unoconv(cls, report, data, timeout, retry=5):
        input_format = report.template_extension
        output_format = report.extension or report.template_extension

        if (weasyprint
                and input_format in {'html', 'xhtml'}
                and output_format == 'pdf'):
            return output_format, weasyprint.HTML(string=data).write_pdf()

        if output_format in MIMETYPES:
            return output_format, data

        dtemp = tempfile.mkdtemp(prefix='trytond_')
        path = os.path.join(
            dtemp, report.report_name + os.extsep + input_format)
        oext = FORMAT2EXT.get(output_format, output_format)
        mode = 'w+' if isinstance(data, str) else 'wb+'
        with open(path, mode) as fp:
            fp.write(data)
        try:
            cmd = ['soffice',
                '--headless', '--nolockcheck', '--nodefault', '--norestore',
                '--convert-to', oext, '--outdir', dtemp, path]
            output = os.path.splitext(path)[0] + os.extsep + oext
            for count in range(retry, -1, -1):
                if count != retry:
                    time.sleep(0.02 * (retry - count))
                subprocess.check_call(cmd, timeout=timeout)
                # ABDC: Please don't judge me... Soffice makes me do this
                # because its returns before file creation.
                nb_retry = 0
                while nb_retry < 10:
                    nb_retry += 1
                    if os.path.exists(output):
                        break
                    time.sleep(0.02)
                if os.path.exists(output):
                    with open(output, 'rb') as fp:
                        return oext, fp.read()
            else:
                logger.error(
                    'fail to convert %s to %s', report.report_name, oext)
                return input_format, data
        finally:
            try:
                os.remove(path)
                os.remove(output)
                os.rmdir(dtemp)
            except OSError:
                pass

    @classmethod
    def convert_api(cls, report, data, timeout):
        # AKE: support printing via external api
        input_format = report.template_extension
        output_format = report.extension or report.template_extension

        if output_format in MIMETYPES:
            return output_format, data

        oext = FORMAT2EXT.get(output_format, output_format)
        url_tpl = config.get('report', 'api')
        url = url_tpl.format(oext=oext)
        files = {'file': ('doc.' + input_format, data)}
        for count in range(config.getint('report', 'unoconv_retry'), -1, -1):
            try:
                r = requests.post(url, files=files, timeout=timeout)
                if r.status_code < 300:
                    return oext, r.content
                else:
                    raise UnoConversionError(r)
            except UnoConversionError:
                if count:
                    time.sleep(0.1)
                    continue
                raise

    @classmethod
    def format_date(cls, value, lang=None, format=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        if lang is None:
            lang = Lang.get()
        return lang.strftime(value, format=format)

    @classmethod
    def format_timedelta(cls, value, converter=None, lang=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        if lang is None:
            lang = Lang.get()
        if not converter:
            converter = TIMEDELTA_DEFAULT_CONVERTER
        if value is None:
            return ''

        def translate(k):
            xml_id = 'ir.msg_timedelta_%s' % k
            translation = gettext(xml_id)
            return translation if translation != xml_id else k

        text = []
        value = value.total_seconds()
        sign = '-' if value < 0 else ''
        value = abs(value)
        converter = sorted(
            converter.items(), key=operator.itemgetter(1), reverse=True)
        values = []
        for k, v in converter:
            part, value = divmod(value, v)
            values.append(part)

        for (k, _), v in zip(converter[:-3], values):
            if v:
                text.append(lang.format('%d', v, True) + translate(k))
        if any(values[-3:]) or not text:
            time = '%02d:%02d' % tuple(values[-3:-1])
            if values[-1] or value:
                time += ':%02d' % values[-1]
            text.append(time)
        text = sign + ' '.join(text)
        if value:
            if not any(values[-3:]):
                # Add space if no time
                text += ' '
            text += ('%.6f' % value)[1:]
        return text

    @classmethod
    def format_currency(cls, value, lang, currency, symbol=True,
            grouping=True):
        pool = Pool()
        Lang = pool.get('ir.lang')
        if lang is None:
            lang = Lang.get()
        return lang.currency(value, currency, symbol, grouping)

    @classmethod
    def format_number(cls, value, lang, digits=2, grouping=True,
            monetary=None):
        pool = Pool()
        Lang = pool.get('ir.lang')
        if lang is None:
            lang = Lang.get()
        return lang.format('%.' + str(digits) + 'f', value,
            grouping=grouping, monetary=monetary)


def get_email(report, record, languages):
    "Return email.mime and title from the report execution"
    pool = Pool()
    ActionReport = pool.get('ir.action.report')
    report_id = None
    if inspect.isclass(report) and issubclass(report, Report):
        Report_ = report
    else:
        if isinstance(report, ActionReport):
            report_name = report.report_name
            report_id = report.id
        else:
            report_name = report
        Report_ = pool.get(report_name, type='report')
    converter = None
    title = None
    msg = MIMEMultipart('alternative')
    msg.add_header('Content-Language', ', '.join(l.code for l in languages))
    for language in languages:
        with Transaction().set_context(language=language.code):
            ext, content, _, title = Report_.execute(
                [record.id], {
                    'action_id': report_id,
                    'language': language,
                    })
        if ext == 'html' and html2text:
            if not converter:
                converter = html2text.HTML2Text()
            part = MIMEText(
                converter.handle(content), 'plain', _charset='utf-8')
            part.add_header('Content-Language', language.code)
            msg.attach(part)
        part = MIMEText(content, ext, _charset='utf-8')
        part.add_header('Content-Language', language.code)
        msg.attach(part)
    return msg, title
