" Userman: RequestHandler subclass."

import logging
import urllib
import weakref
import smtplib
from email.mime.text import MIMEText

import tornado.web
import couchdb

from . import settings
from . import constants
from . import utils


class RequestHandler(tornado.web.RequestHandler):
    "Base request handler."

    def prepare(self):
        self.db = utils.get_db()
        self._cache = weakref.WeakValueDictionary()

    def get_template_namespace(self):
        result = super(RequestHandler, self).get_template_namespace()
        result['settings'] = settings
        result['constants'] = constants
        result['current_user'] = self.get_current_user()
        result['is_admin'] = self.is_admin()
        result['self_url'] = self.request.uri
        return result

    def get_absolute_url(self, name, *args, **kwargs):
        "Get the absolute URL given the reverse_url name and any arguments."
        if name is None:
            path = ''
        else:
            path = self.reverse_url(name, *args)
        url = settings['BASE_URL'].rstrip('/') + path
        if kwargs:
            url += '?' + urllib.urlencode(kwargs)
        return url

    def get_current_user(self):
        "Get the currently logged-in user."
        try:
            if self._user.get('status') != constants.ACTIVE:
                self.set_secure_cookie(constants.USER_COOKIE_NAME, '')
                return None
        except AttributeError:
            email = self.get_secure_cookie(constants.USER_COOKIE_NAME)
            if not email: return None
            try:
                user = self.get_user(email)
                if user.get('status') != constants.ACTIVE:
                    raise tornado.web.HTTPError(400)
            except tornado.web.HTTPError:
                return None
            self._user = user
        return self._user

    def get_user(self, email):
        "Get the user document by its email."
        try:
            key = "{0}:{1}".format(constants.USER, email)
            return self._cache[key]
        except KeyError:
            result = list(self.db.view('user/email', include_docs=True)[email])
            if len(result) == 1:
                doc = result[0].doc
                self._cache[key] = self._cache[doc.id] = doc
                return doc
            raise tornado.web.HTTPError(404, 'no such user')

    def get_service(self, name):
        "Get the service document by its name."
        try:
            key = "{0}:{1}".format(constants.SERVICE, name)
            return self._cache[key]
        except KeyError:
            result = list(self.db.view('service/name', include_docs=True)[name])
            if len(result) == 1:
                doc = result[0].doc
                self._cache[key] = self._cache[doc.id] = doc
                return doc
            raise tornado.web.HTTPError(404, 'no such service')

    def get_all_services(self):
        return [self.get_service(r.key) for r in self.db.view('service/name')]
                          
    def get_team(self, name):
        "Get the team document by its name."
        try:
            key = "{0}:{1}".format(constants.SERVICE, name)
            return self._cache[key]
        except KeyError:
            result = list(self.db.view('team/name', include_docs=True)[name])
            if len(result) == 1:
                doc = result[0].doc
                self._cache[key] = self._cache[doc.id] = doc
                return doc
            raise tornado.web.HTTPError(404, 'no such team')

    def is_admin(self):
        "Is the current user admin?"
        if not self.current_user: return False
        return self.current_user['role'] == 'admin'

    def check_admin(self):
        "Check that the current user is admin."
        if not self.is_admin():
            raise tornado.web.HTTPError(403, 'admin role required')

    def get_doc(self, id, doctype=None):
        "Return the document given by its id, optionally checking the doctype."
        try:
            return self._cache[id]
        except KeyError:
            try:
                doc = self.db[id]
                if doctype:
                    if doctype != doc.get(constants.DB_DOCTYPE):
                        msg = 'invalid doctype'
                        raise ValueError(msg)
                self._cache[id] = doc
                    
                return doc
            except couchdb.ResourceNotFound:
                raise ValueError('no such document')

    def get_logs(self, id):
        "Return the log documents for the given doc id."
        view = self.db.view('log/doc', include_docs=True)
        return sorted([r.doc for r in view[id]],
                      cmp=utils.cmp_modified,
                      reverse=True)

    def send_email(self, user, subject, text):
        self.check_admin()
        mail = MIMEText(text)
        mail['Subject'] = subject
        mail['From'] = self.current_user['email']
        mail['To'] = user['email']
        server = smtplib.SMTP(settings['EMAIL']['SERVER'])
        if settings['EMAIL'].get('TLS'):
            server.starttls()
        try:
            server.login(settings['EMAIL']['ACCOUNT'],
                         settings['EMAIL']['PASSWORD'])
        except KeyError:
            pass
        server.sendmail(self.current_user['email'],
                        [user['email']],
                        mail.as_string())
        server.quit()
