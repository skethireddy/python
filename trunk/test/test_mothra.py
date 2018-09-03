import mothra
import svn_cli
import os
import pickle
import time
import datetime
from dynaconf import settings
from flask import Flask, request
app = Flask(__name__)

def test_health():
    with app.test_request_context('/health', method='GET'):
        # now you can do something with the request until the
        # end of the with block, such as basic assertions:
        assert request.path == '/health'
        assert request.method == 'GET'
        #print request.

def _test_pickle():
    try:
        last_rundate = pickle.load(open("rundate.p", "rb"))
        print 'last_rundate: ', last_rundate
    except:
        pass
    time.sleep(5)
    pickle.dump(datetime.datetime.now(), open("rundate.p", "wb"))

def _test_sv_co_or_update_with_add():
    local_path = 'data'
    mothra.setup_logging()
    mothra.clean()
    try:
        svn_cli.svn_delete(settings.SVN_URL + '/junk.txt')
    except:
        pass
    svn_cli.svn_checkout_or_update(local_path, settings.SVN_URL)

    # Add a file
    f = open('data/junk.txt', 'w')
    f.write('x x x x x')
    f.close()
    svn_cli.svn_add('data/junk.txt')

    svn_cli.svn_commit(local_path)


def _test_sv_co_or_update_with_rename():
    ''' Expects data/junk.txt '''
    local_path = 'data'
    mothra.setup_logging()
    mothra.clean()
    svn_cli.svn_checkout_or_update(local_path, settings.SVN_URL)

    # Rename a file
    os.rename('data/junk.txt', 'data/garbage.txt')
    svn_cli.svn_add('data/garbage.txt')

    svn_cli.svn_commit(local_path)


def _test_sv_co_or_update_with_change():
    ''' Expects data/junk.txt '''
    local_path = 'data'
    mothra.setup_logging()
    mothra.clean()
    svn_cli.svn_checkout_or_update(local_path, settings.SVN_URL)

    # Change a file
    f = open('data/junk.txt', 'w')
    f.write('a a a a a a')
    f.close()

    svn_cli.svn_commit(local_path)


def _test_process_bugs():
    mothra.setup_logging()
    mothra.clean()

    bugs = []
    #for i in range(5):
    #    bugs.append({'BUG_ID': str(i), 'PRODUCT': 'Lemon'})
    sample = {u'fixedVersions': u'11.5.0', u'functionalChange': u'---', u'foundOn': u'11.4.0',
         u'externalTitle': u'BIG-IP AVR v11.3 HF5 - Time Zone system affects the DoS graph time.',
         u'assignedToRealName': u'Orit Margalit', u'impact': u'AVR reports and graph data dose not make sense',
         u'priority': 10, u'opened': '',
         u'workaround': u'This issue has no workaround at this time.',
         u'title': u'AVR issues with timezone and time adjustments', u'affectedModules': u'AVR',
         u'knownAffectedVersions': u'11.4.0, 11.3.0',
         u'symptoms': u'Impact: When the timezone (System > Platform > Time Zone) is in any time zone under WEST (for example, the time zone for "Europe/Lisbon"), or EST, the time shown in the Reporting > DoS > Application for the "Time Period" of "Last Hour" is an hour ahead of the time system.',
         u'assignedTo': u'o.margalit@f5.com', u'solutionURL': u'https://support.f5.com/csp/#/article/K10473262',
         u'bugType': u'Defect', u'hidden': 0, u'conditions': u'Time change to past on already working system.',
         u'status': u'Verified', u'fixText': u'Fix logic conditions regarding time chance.', u'product': u'BIG-IP',
         u'behaviorChange': u'', u'component': u'AVR_DP', u'bug_id': 420290, u'severity': u'3-Major',
         u'lastModified': '', u'solutionStatus': u'Published', u'alias': 420290}
    bugs.append(sample)


    for bug in bugs:
        print 'bug: ', bug
        local_path = os.path.join('data', str(bug['bug_id'])) + '.html'
        url = settings.SVN_URL + '/' + str(bug['bug_id']) + '.html'
        mothra.write_file(bug, local_path)
        mothra.svn_import(local_path, url)
    #mothra.svn_import()