"""Basic scaffolding for handling OAuth"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/08_oauth.ipynb.

# %% auto 0
__all__ = ['http_patterns', 'GoogleAppClient', 'GitHubAppClient', 'HuggingFaceClient', 'DiscordAppClient', 'redir_url',
           'url_match', 'OAuth']

# %% ../nbs/api/08_oauth.ipynb
from .common import *
from oauthlib.oauth2 import WebApplicationClient
from urllib.parse import urlparse, urlencode, parse_qs, quote, unquote
import secrets, httpx

# %% ../nbs/api/08_oauth.ipynb
class _AppClient(WebApplicationClient):
    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        super().__init__(client_id, code=code, scope=scope, **kwargs)
        self.client_secret = client_secret

# %% ../nbs/api/08_oauth.ipynb
class GoogleAppClient(_AppClient):
    "A `WebApplicationClient` for Google oauth2"
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://www.googleapis.com/oauth2/v4/token"
    info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    id_key = 'sub'
    
    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        scope_pre = "https://www.googleapis.com/auth/userinfo"
        if not scope: scope=["openid", f"{scope_pre}.email", f"{scope_pre}.profile"]
        super().__init__(client_id, client_secret, code=code, scope=scope, **kwargs)
    
    @classmethod
    def from_file(cls, fname, code=None, scope=None, **kwargs):
        cred = Path(fname).read_json()['web']
        return cls(cred['client_id'], client_secret=cred['client_secret'], code=code, scope=scope, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class GitHubAppClient(_AppClient):
    "A `WebApplicationClient` for GitHub oauth2"
    base_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    info_url = "https://api.github.com/user"
    id_key = 'id'

    def __init__(self, client_id, client_secret, code=None, scope=None, **kwargs):
        super().__init__(client_id, client_secret, code=code, scope=scope, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class HuggingFaceClient(_AppClient):
    "A `WebApplicationClient` for HuggingFace oauth2"

    base_url = "https://huggingface.co/oauth/authorize"
    token_url = "https://huggingface.co/oauth/token"
    info_url = "https://huggingface.co/oauth/userinfo"
    id_key = 'sub'
    
    def __init__(self, client_id, client_secret, code=None, scope=None, state=None, **kwargs):
        if not scope: scope=["openid","profile"]
        if not state: state=secrets.token_urlsafe(16)
        super().__init__(client_id, client_secret, code=code, scope=scope, state=state, **kwargs)

# %% ../nbs/api/08_oauth.ipynb
class DiscordAppClient(_AppClient):
    "A `WebApplicationClient` for Discord oauth2"
    base_url = "https://discord.com/oauth2/authorize"
    token_url = "https://discord.com/api/oauth2/token"
    revoke_url = "https://discord.com/api/oauth2/token/revoke"
    id_key = 'id'

    def __init__(self, client_id, client_secret, is_user=False, perms=0, scope=None, **kwargs):
        if not scope: scope="applications.commands applications.commands.permissions.update identify"
        self.integration_type = 1 if is_user else 0
        self.perms = perms
        super().__init__(client_id, client_secret, scope=scope, **kwargs)

    def login_link(self):
        d = dict(response_type='code', client_id=self.client_id,
                 integration_type=self.integration_type, scope=self.scope) #, permissions=self.perms, prompt='consent')
        return f'{self.base_url}?' + urlencode(d)

    def parse_response(self, code):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = dict(grant_type='authorization_code', code=code)#, redirect_uri=self.redirect_uri)
        r = httpx.post(self.token_url, data=data, headers=headers, auth=(self.client_id, self.client_secret))
        r.raise_for_status()
        self.parse_request_body_response(r.text)

# %% ../nbs/api/08_oauth.ipynb
@patch
def login_link(self:WebApplicationClient, redirect_uri, scope=None, state=None):
    "Get a login link for this client"
    if not scope: scope=self.scope
    if not state: state=getattr(self, 'state', None)
    return self.prepare_request_uri(self.base_url, redirect_uri, scope, state=state)

# %% ../nbs/api/08_oauth.ipynb
def redir_url(request, redir_path, scheme='https'):
    "Get the redir url for the host in `request`"
    return f"{scheme}://{request.url.netloc}{redir_path}"

# %% ../nbs/api/08_oauth.ipynb
@patch
def parse_response(self:_AppClient, code, redirect_uri):
    "Get the token from the oauth2 server response"
    payload = dict(code=code, redirect_uri=redirect_uri, client_id=self.client_id,
                   client_secret=self.client_secret, grant_type='authorization_code')
    r = httpx.post(self.token_url, json=payload)
    r.raise_for_status()
    self.parse_request_body_response(r.text)

# %% ../nbs/api/08_oauth.ipynb
@patch
def get_info(self:_AppClient, token=None):
    "Get the info for authenticated user"
    if not token: token = self.token["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    return httpx.get(self.info_url, headers=headers).json()

# %% ../nbs/api/08_oauth.ipynb
@patch
def retr_info(self:_AppClient, code, redirect_uri):
    "Combines `parse_response` and `get_info`"
    self.parse_response(code, redirect_uri)
    return self.get_info()

# %% ../nbs/api/08_oauth.ipynb
@patch
def retr_id(self:_AppClient, code, redirect_uri):
    "Call `retr_info` and then return id/subscriber value"
    return self.retr_info(code, redirect_uri)[self.id_key]

# %% ../nbs/api/08_oauth.ipynb
http_patterns = (r'^(localhost|127\.0\.0\.1)(:\d+)?$',)
def url_match(url, patterns=http_patterns):
    return any(re.match(pattern, url.netloc.split(':')[0]) for pattern in patterns)

# %% ../nbs/api/08_oauth.ipynb
class OAuth:
    def __init__(self, app, cli, skip=None, redir_path='/redirect', error_path='/error', logout_path='/logout', login_path='/login', https=True, http_patterns=http_patterns):
        if not skip: skip = [redir_path,error_path,login_path]
        store_attr()
        def before(req, session):
            auth = req.scope['auth'] = session.get('auth')
            if not auth: return RedirectResponse(self.login_path, status_code=303)
            info = AttrDictDefault(cli.get_info(auth))
            if not self._chk_auth(info, session): return RedirectResponse(self.login_path, status_code=303)

        app.before.append(Beforeware(before, skip=skip))

        @app.get(redir_path)
        def redirect(req, session, code:str=None, error:str=None, state:str=None):
            if not code: session['oauth_error']=error; return RedirectResponse(self.error_path, status_code=303)
            scheme = 'http' if url_match(req.url,self.http_patterns) or not self.https else 'https'
            base_url = f"{scheme}://{req.url.netloc}"
            info = AttrDictDefault(cli.retr_info(code, base_url+redir_path))
            if not self._chk_auth(info, session): return RedirectResponse(self.login_path, status_code=303)
            session['auth'] = cli.token['access_token']
            return self.login(info, state, session=session)

        @app.get(logout_path)
        def logout(session):
            session.pop('auth', None)
            return self.logout(session)

    def redir_url(self, req): 
        scheme = 'http' if url_match(req.url,self.http_patterns) or not self.https else 'https'
        return redir_url(req, self.redir_path, scheme)
    def login_link(self, req, scope=None, state=None): return self.cli.login_link(self.redir_url(req), scope=scope, state=state)

    def login(self, info, state, session): raise NotImplementedError()
    def logout(self, session): return RedirectResponse(self.login_path, status_code=303)
    def chk_auth(self, info, ident, session): raise NotImplementedError()
    def _chk_auth(self, info, session):
        ident = info.get(self.cli.id_key)
        return ident and self.chk_auth(info, ident, session)
