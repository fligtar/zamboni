from django.conf import settings
from django.conf.urls.defaults import patterns, url, include

from piston.resource import Resource
from piston import authentication

from api import handlers
from api import views
from zadmin import jinja_for_django

API_CACHE_TIMEOUT = getattr(settings, 'API_CACHE_TIMEOUT', 500)


# Wrap class views in a lambda call so we get an fresh instance of the class
# for thread-safety.
def class_view(cls):
    inner = lambda *args, **kw: cls()(*args, **kw)
    return inner


# Regular expressions that we use in our urls.
type_regexp = '/(?P<addon_type>[^/]*)'
limit_regexp = '/(?P<limit>\d*)'
platform_regexp = '/(?P<platform>\w*)'
version_regexp = '/(?P<version>[^/]*)'


def build_urls(base, appendages):
    """
    Many of our urls build off each other:
    e.g.
    /search/:query
    /search/:query/:type
    .
    .
    /search/:query/:type/:limit/:platform/:version
    """
    urls = [base]
    for i in range(len(appendages)):
        urls.append(base + ''.join(appendages[:i + 1]))

    return urls


base_search_regexp = r'search/(?P<query>[^/]+)'
appendages = [type_regexp, limit_regexp, platform_regexp, version_regexp]
search_regexps = build_urls(base_search_regexp, appendages)

base_list_regexp = r'list'
appendages.insert(0, '/(?P<list_type>[^/]+)')
list_regexps = build_urls(base_list_regexp, appendages)


api_patterns = patterns('',
    # Addon_details
    url('addon/(?P<addon_id>\d+)$', class_view(views.AddonDetailView),
        name='api.addon_detail'),)

for regexp in search_regexps:
    api_patterns += patterns('',
        url(regexp + '/?$', class_view(views.SearchView), name='api.search'))

for regexp in list_regexps:
    api_patterns += patterns('',
            url(regexp + '/?$', class_view(views.ListView), name='api.list'))


ad = dict(authentication=authentication.OAuthAuthentication())
user_resource = Resource(handler=handlers.UserHandler, **ad)

jfd = lambda a, b, c: jinja_for_django(a, b, context_instance=c)
authentication.render_to_response = jfd

piston_patterns = patterns('',
    url(r'^user/$', user_resource, name='api.user'),
)

urlpatterns = patterns('',
    # Redirect api requests without versions
    url('^((?:addon|search|list)/.*)$', views.redirect_view),

    # Piston
    url(r'^2/', include(piston_patterns)),

    # Append api_version to the real api views
    url(r'^(?P<api_version>\d+|\d+.\d+)/', include(api_patterns)),

)
