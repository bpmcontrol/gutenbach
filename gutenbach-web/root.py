"""Main Controller"""
from sipbmp3web.lib.base import BaseController
from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _
#from tg import redirect, validate
from sipbmp3web.model import DBSession, metadata
from sipbmp3web.controllers.error import ErrorController
from sipbmp3web import model
from catwalk.tg2 import Catwalk
from repoze.what import predicates
from sipbmp3web.controllers.secure import SecureController

class RootController(BaseController):
    admin = Catwalk(model, DBSession)
    error = ErrorController()

    @expose('sipbmp3web.templates.index')
    def index(self):
        return dict(page='index')

    @expose('sipbmp3web.templates.about')
    def about(self):
        return dict(page='about')

    @expose('sipbmp3web.templates.authentication')
    def auth(self):
        return dict(page='auth')

    @expose('sipbmp3web.templates.index')
    @require(predicates.has_permission('manage', msg=_('Only for managers')))
    def manage_permission_only(self, **kw):
        return dict(page='managers stuff')

    @expose('sipbmp3web.templates.index')
    @require(predicates.is_user('editor', msg=_('Only for the editor')))
    def editor_user_only(self, **kw):
        return dict(page='editor stuff')

    @expose('sipbmp3web.templates.login')
    def login(self, came_from=url('/')):
        login_counter = request.environ['repoze.who.logins']
        if login_counter > 0:
            flash(_('Wrong credentials'), 'warning')
        return dict(page='login', login_counter=str(login_counter),
                    came_from=came_from)

    @expose()
    def post_login(self, came_from=url('/')):
        if not request.identity:
            login_counter = request.environ['repoze.who.logins'] + 1
            redirect(url('/login', came_from=came_from, __logins=login_counter))
        userid = request.identity['repoze.who.userid']
        flash(_('Welcome back, %s!') % userid)
        redirect(came_from)

    @expose()
    def post_logout(self, came_from=url('/')):
        flash(_('We hope to see you soon!'))
        redirect(came_from)
