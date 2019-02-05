#!/usr/bin/env python
"""
    Get a bug info from a database into HTML and then into Subversion.
"""
import mysql.connector
import os
import sys
import glob
import logging
import logging.handlers, logging.config
import svn_cli
import pickle
import yaml
import datetime
import time
import json
from dynaconf import settings
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)
DEFAULT_BUG_LIMIT = 15000


def main(bug_id=None):
    """
    Subversion update or checkout, render as HTML to disk, and then commit

    Within called function render_bugs() a Subversion delete will be issued if hidden=1
    If bug_id is included as an argument 1) index file generation will get skipped;
    and 2) the last run date won't get saved to disk
    """
    row_count = 0
    start = time.time()
    start_datetime = datetime.datetime.now()
    last_rundate = None
    logger.info('Begin processing')
    try:
        if not os.path.exists(settings.DATA_DIR):
            os.makedirs(settings.DATA_DIR)

        if settings.USE_SVN:
            logger.info('Checkout or update ...')
            svn_cli.svn_checkout_or_update(settings.DATA_DIR, settings.SVN_URL)

        if not bug_id:
            try:
                last_rundate = get_last_run_date()
                logger.info('Last run date: %s', last_rundate)
            except:
                pass

        logger.info('Processing bugs...')
        row_count = render_bugs(bug_id, last_rundate)
        logger.info('Processed %s bugs', str(row_count))

        if not bug_id and row_count > 0:
            logger.info('Building index...')
            build_index()

        if settings.USE_SVN and row_count > 0:
            logger.info('Subversion add...')
            out = svn_cli.svn_add(settings.DATA_DIR)
            logger.debug('Subversion add output: %s', out)
            logger.info('Subversion commit ...')
            out = svn_cli.svn_commit(settings.DATA_DIR, 'Mothra commit bug files.')
            logger.debug('Subversion commit output: %s', out)

        end = time.time()

        if not bug_id:
            logger.info('Save last run date: %s', start_datetime)
            set_last_run_date(start_datetime)

        logger.info('Processing completed in %s seconds', str(end - start))
    except:
        logger.error('Error processing bugs', exc_info=True)
    return row_count


def get_bug(bug_id):
    """
    Get one bug as JSON
    """
    cnx = get_connection()
    cursor = cnx.cursor()
    cursor.execute('select * from ' + settings.BUG_TABLE + ' where bug_id = %s', (bug_id,))
    row_headers = [x[0] for x in cursor.description]  # extract row headers
    rv = cursor.fetchall()
    json_data = []
    for result in rv:
        json_data.append(dict(zip(row_headers, result)))
    return json.dumps(json_data, default=default_converter, sort_keys=True, indent=4)


def render_bugs(bug_id=None, last_rundate=None):
    """
    Call database, iterate through result set, squeeze
    through templates write to file system.
    If hidden=true issue a Subversion delete
    """
    cnx = get_connection()
    cursor = cnx.cursor(dictionary=True, buffered=True)

    try:
        if bug_id:
            cursor.execute('select * from ' + settings.BUG_TABLE + ' where bug_id = %s', (bug_id,))
        elif last_rundate:
            cursor.execute('select * from ' + settings.BUG_TABLE +
                           ' where buglastmodified > %s limit %s', (last_rundate, settings.BUG_LIMIT,))
        else:
            cursor.execute('select * from ' + settings.BUG_TABLE + ' limit %s', (settings.BUG_LIMIT,))

        row_count = cursor.rowcount

        for row in cursor:
            bugid = str(row['bug_id'])
            local_path = os.path.join(settings.DATA_DIR, 'ID' + bugid) + '.html'
            hidden = bool(row['hidden'])
            if hidden:
                logger.debug('Delete: %s (%s)', bugid, local_path)
                try:
                    svn_cli.svn_delete(local_path, 'Mothra delete of bug ' + bugid)
                except:
                    logger.warn('Error deleting: %s (%s); probably not a big deal', bugid, local_path)
            else:
                bug_type = str(row['bugType'])
                logger.debug('Write: %s (%s) with type=%s', bugid, local_path, bug_type)
                enrich(row)
                template_file = settings.BUG_TEMPLATE if bug_type != 'Vulnerability' else settings.BUG_CVE_TEMPLATE
                write_bug_file(row, local_path, template_file)

    finally:
        cursor.close()
        cnx.close()

    return row_count


def enrich(row):
    """
    Manipulate context passed to template
    """
    row['askf5_url_root'] = settings.ASKF5_URL_ROOT
    if row['solutionURL']:
        solution_url = str(row['solutionURL'])
        # Create alternate_related_kb_id
        kblist = solution_url.split(',')
        kblist_k_less = [kb.strip()[1:] for kb in kblist]  # remove Ks
        row['alternate_related_kb_id'] = ', '.join(kblist_k_less)
        # Update cve_ID; replace spaces with commas
    if row['cve_ID']:
        cve_id = row['cve_ID'].split(' ')
        row['cve_ID'] = ', '.join(cve_id)


def build_index():
    """
    Build index.html using a template
    """
    path = settings.DATA_DIR
    index_file_path = os.path.join(path, 'index.html')

    bugs = []
    now = None
    for file in glob.glob(os.path.join(path, 'ID*.html')):
        bug_file = os.path.basename(file)
        bug_id = bug_file[2:].split(".", 1)[0]  # Isolate bug id from filename
        bug = dict(id=bug_id, file=bug_file, url=settings.CDN_URL_ROOT)
        bugs.append(bug)
        now = datetime.datetime.utcnow()
    with open(index_file_path, 'w') as index_file:
        output = render(settings.INDEX_TEMPLATE, {'bugs': bugs, 'timestamp': now})
        index_file.write(output.encode('utf-8'))


def set_last_run_date(last_run_date):
    """
    Serialize the last run date to disk using pickle
    """
    pickle.dump(last_run_date, open(settings.STATE_FILE, "wb"))


def get_last_run_date():
    """
    Get the last run date from disk using pickle
    """
    try:
        return pickle.load(open(settings.STATE_FILE, "rb"))
    except:
        return None


def reset():
    """
    Remove last run date on disk using pickle
    """
    logger.debug('Reset: remove last run date on disk.')
    try:
        os.remove(settings.STATE_FILE)
    except OSError:
        pass


def write_bug_file(context, path, bug_template):
    """
    Render bug data and write to disk.
    The Bug ID appears in the file names.
    """
    with open(path, 'w') as bug_file:
        output = render(bug_template, context)
        bug_file.write(output.encode('utf-8'))


def get_connection():
    return mysql.connector.connect(user=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
                                   host=settings.MYSQL_HOST, port=settings.MYSQL_PORT,
                                   database=settings.MYSQL_DB)


def render(tpl_path, context):
    """
    Use Jinja2 to render HTML using a template
    """
    path, filename = os.path.split(tpl_path)
    return Environment(
        loader=FileSystemLoader(path or './'),
        trim_blocks=True,
        lstrip_blocks=True
    ).get_template(filename).render(context)


def setup_logging(
        default_path='logging.yaml',
        default_level=logging.INFO,
        env_key='MOTHRA_LOG_CFG'
):
    """ Setup logging configuration.
        Can use environment variable MOTHRA_LOG_CFG=my_logging.yaml
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def default_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


if __name__ == '__main__':
    setup_logging()
    command = None
    if len(sys.argv) > 1:
        command = str(sys.argv[1]).strip()
        if command == 'render':
            if len(sys.argv) > 2:
                bug_id = str(sys.argv[2]).strip()
                main(bug_id)
            else:
                main()
        elif command == 'reset':
            reset()
        elif command == 'last':
            print('Last run date: ' + str(get_last_run_date()))
        elif command == 'bug':
            if len(sys.argv) > 2:
                bug_id = str(sys.argv[2]).strip()
                print(get_bug(bug_id))
        elif command == 'help':
            help = """
              /// MOTHRA ///

              Usage
                python mothra.py <command>
              Commands
                render [bug_id]  Renders bugs as HTML. This is the default. bug_id is optional.
                reset            Deletes the last run date from disk.'
                last             Shows last run date, if one exists on disk.'
                delete bug_id    Deletes bug file (via Subversion). Bugs to delete have hidden=1'
            """
            print(help)
    else:
        main()
