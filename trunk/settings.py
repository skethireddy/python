DYNACONF_NAMESPACE = 'MOTHRA'

USE_SVN = True
DATA_DIR = 'data'
DEBUG = False
STATE_FILE = 'rundate.p'
BUG_TEMPLATE = 'templates/bug-template.html'
INDEX_TEMPLATE = 'templates/index-template.html'


MYSQL_HOST = 'rdtprod.pdsea.f5net.com'
MYSQL_PORT = '3306'
MYSQL_USER = 'someone'
MYSQL_PASSWORD = 'XXXXX'
MYSQL_DB = 'BugFaceProd'
BUG_TABLE = 'BugFaceProd.bug'

BUG_LIMIT = 15000

SVN_USER = 'someone'
SVN_PASSWORD = 'XXXXX'
SVN_URL= 'https://itsvn.f5net.com/svn/cdn.f5.com/test/product/bugtracker'
# CDN_URL_ROOT has no trailing slash
CDN_URL_ROOT = 'https://cdn-test.f5.com/product/bugtracker'


#ASKF5_URL_ROOT = 'https://support.tst.dmz/csp/article'
ASKF5_URL_ROOT = 'https://support.f5.com/csp/article'