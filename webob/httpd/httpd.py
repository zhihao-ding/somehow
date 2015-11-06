#!/usr/bin/env python

import os
import sys
import re
import threading
import urllib
import tempita
import mimetypes

from webob import Request
from webob import Response
from webob import exc

from wsgiref.simple_server import make_server

var_regex = re.compile(r'''
\{		# The exact character "{"
(\w+)		# The variable name (restricted to a-z, 0-9, _)
(?::([^}]+))?	# The optional :regex part
\}		# The exact character "}"
''', re.VERBOSE)

def template_to_regex(template):
    regex = ''
    last_pos = 0
    for match in var_regex.finditer(template):
        regex += re.escape(template[last_pos:match.start()])
        var_name = match.group(1)
        expr = match.group(2) or '[^/]+'
        expr = '(?P<%s>%s)' % (var_name, expr)
        regex += expr
        last_pos = match.end()
    regex += re.escape(template[last_pos:])
    regex = '^%s$' % regex
    return regex

def load_controller(string):
    module_name, func_name = string.split(':', 1)
    __import__(module_name)
    module = sys.modules[module_name]
    func = getattr(module, func_name)
    return func

def get_mimetype(filename):
    type, encoding = mimetypes.guess_type(filename)
    return type or 'application/octet-stream'

class Router(object):
    def __init__(self):
        self.routes = []

    def add_route(self, template, controller, **vars):
        if isinstance(controller, basestring):
            controller = load_controller(controller)
        self.routes.append((re.compile(template_to_regex(template)),
                           controller, vars))

    def add_route_ex(self, regex, controller, **vars):
        if isinstance(controller, basestring):
            controller = load_controller(controller)
        self.routes.append((re.compile(regex),
                           controller, vars))

    def _get_static_file(self, req):
        path_info = req.path_info
        if path_info == '/':
            path_info = '/index.html'
        filename = 'web' + path_info
        try:
            res = Response(content_type=get_mimetype(filename))
            with open(filename) as file:
                res.body = file.read()
        except:
            res = exc.HTTPNotFound()
        return res

    def __call__(self, environ, start_response):
        req = Request(environ)
        for regex, controller, vars in self.routes:
            match = regex.match(req.path_info)
            if match:
                req.urlvars = match.groupdict()
                req.urlvars.update(vars)
                return controller(environ, start_response)
        # if mismatch controller try to get it as files
        res = self._get_static_file(req)
        return res(environ, start_response)

def controller(func):
    def replacement(environ, start_response):
        req = Request(environ)
        try:
            res = func(req, **req.urlvars)
        except exc.HTTPException, e:
            res = e
        if isinstance(res, basestring):
            res = Response(body=res)
        return res(environ, start_response)
    return replacement

def rest_controller(cls):
    def replacement(environ, start_response):
        req = Request(environ)
        try:
            instance = cls(req, **req.urlvars)
            action = req.urlvars.get('action')
            if action:
                action += '_' + req.method.lower()
            else:
                action = req.method.lower()
            try:
                method = getattr(instance, action)
            except AttributeError:
                raise exc.HTTPNotFound("No action %s" % action)
            res = method()
            if isinstance(res, basestring):
                res = Response(body=res)
        except exc.HTTPException, e:
            res = e
        return res(environ, start_response)
    return replacement

class Localized(object):
    def __init__(self):
        self.local = threading.local()
    def register(self, object):
        self.local.object = object
    def unregister(self):
        del self.local.object
    def __call__(self):
        try:
            return self.local.object
        except AttributeError:
            raise TypeError("No object has been registered for this thread") 

get_request = Localized()

class RegisterRequest(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        req = Request(environ)
        get_request.register(req)
        try:
            return self.app(environ, start_response)
        finally:
            get_request.unregister()

def url(*segments, **vars):
    '''
	>>> get_request.register(Request.blank('http://localhost/'))
	>>> url('article', 1)
	'http://localhost/article/1'
	>>> url('search', q='some query')
	'http://localhost/search?q=some+query'
    '''
    base_url = get_request().application_url
    path = '/'.join(str(s) for s in segments)
    if not path.startswith('/'):
        path = '/' + path
    if vars:
        path += '?' + urllib.urlencode(vars)
    return base_url + path

def render(template, **vars):
    if isinstance(template, basestring):
        caller_location = sys._getframe(1).f_globals['__file__']
        filename = os.path.join(os.path.dirname(caller_location), template)
        template = tempita.HTMLTemplate.from_filename(filename)
    vars.setdefault('request', get_request())
    return template.substitute(vars)

# TODO:
# 1. Configuration
# 2. Making your routes debuggable
# 3. Exception catching and other basic infrastructure
# 4. Database connections
# 5. Form handing
# 6. Authentication

if __name__ == '__main__':
    try:
        router = Router()
        httpd = make_server('localhost', 8080, RegisterRequest(router))
        print "Serving on port 8080 ..."
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "Bye!"

