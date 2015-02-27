# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys
import json
import traceback
import StringIO
import gzip
from BaseHTTPServer import BaseHTTPRequestHandler, DEFAULT_ERROR_MESSAGE
from trytond.protocols.jsonrpc import JSONDecoder, JSONEncoder
from trytond.protocols.dispatcher import dispatch
from trytond.config import config
from trytond.pool import Pool
from trytond.exceptions import UserError, UserWarning, NotLogged, \
    ConcurrencyException


def get_jsonrpc_app():
    config.update_etc()

    Pool.start()

    def f(environ, start_response):
        'JSON-RPC dispatcher'
        def error_response(code):
            message, explain = BaseHTTPRequestHandler.responses[code]
            start_response('%d %s' % (code, message),
                        [('Content-Type', 'text/html')])
            return [DEFAULT_ERROR_MESSAGE % locals()]

        if environ['REQUEST_METHOD'] == 'POST':
            body = ''
            try:
                length = int(environ.get('CONTENT_LENGTH', '0'))
            except ValueError:
                length = 0
            body = environ['wsgi.input'].read(length)
            if environ.get('HTTP_CONTENT_ENCODING') == 'gzip':
                f = StringIO.StringIO(body)
                gzf = gzip.GzipFile(mode="rb", fileobj=f)
                try:
                    decoded = gzf.read()
                except IOError:
                    return error_response(400)
                f.close()
                gzf.close()
                body = decoded
            try:
                rawreq = json.loads(body, object_hook=JSONDecoder())
            except ValueError:
                return error_response(501)
            req_id = rawreq.get('id', 0)
            method = rawreq['method']
            params = rawreq.get('params', [])

            response = {'id': req_id}
            database_name = environ['PATH_INFO'][1:]
            if database_name.startswith('sao/'):
                database_name = database_name[4:]
            method_list = method.split('.')
            object_type = method_list[0]
            object_name = '.'.join(method_list[1:-1])
            method = method_list[-1]
            args = (
                environ['SERVER_NAME'],
                int(environ['SERVER_PORT']),
                'JSON-RPC',
                database_name,
                params[0],
                params[1],
                object_type,
                object_name,
                method
            ) + tuple(params[2:])
            try:
                response['result'] = dispatch(*args)
            except (UserError, UserWarning, NotLogged,
                    ConcurrencyException), exception:
                response['error'] = exception.args
            except Exception:
                tb_s = ''.join(traceback.format_exception(*sys.exc_info()))
                for path in sys.path:
                    tb_s = tb_s.replace(path, '')
                # report exception back to server
                response['error'] = (str(sys.exc_value), tb_s)

            start_response('200 OK',
                        [('Content-Type', 'application/json-rpc')])
            return [json.dumps(response, cls=JSONEncoder)]
        else:
            return error_response(501)
    return f


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    jsonrpc_app = get_jsonrpc_app()
    httpd = make_server('', 8000, jsonrpc_app)
    httpd.serve_forever()
