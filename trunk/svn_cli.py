#!/usr/bin/env python
'''
    Subversion CLI Helper
'''
import subprocess
import os
from dynaconf import settings

def svn_delete(path, message):
    return subprocess.check_output(['svn', '--username', settings.SVN_USER, \
                                    '--password', settings.SVN_PASSWORD, 'delete', \
                                    path, '--force'])

def svn_commit(local_path, message):
    return subprocess.check_output(['svn', '--username', settings.SVN_USER, \
                                   '--password', settings.SVN_PASSWORD, 'commit', \
                                   local_path, '-m', message])

def svn_checkout_or_update(local_path, url):
    svn_checkout(local_path, url)
    svn_update(local_path)


def svn_checkout(local_path, url):
    try:
        return subprocess.check_output(['svn', '--username', settings.SVN_USER, \
                                        '--password', settings.SVN_PASSWORD, 'co', url, local_path])
    except:
        pass

def svn_update(local_path):
    return subprocess.check_output(['svn', '--username', settings.SVN_USER, \
                                    '--password', settings.SVN_PASSWORD, 'update', local_path, '--force'])

def svn_add(local_path):
    """
    Drop into the directory and then out again to get around issues on some systems
    """
    os.chdir(settings.DATA_DIR)
    out = subprocess.call(['svn', '--username', settings.SVN_USER, \
                         '--password', settings.SVN_PASSWORD, '--force', 'add', '.'])
    os.chdir('..')
    return out