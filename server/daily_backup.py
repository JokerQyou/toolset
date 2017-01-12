#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Daily backup tool that
- dumps MySQL / MariaDB databases;
- backs up files;
- syncs archive into cloud storage;
- pushe a notification to yout;
'''

from datetime import datetime
import os
import io
import sys
import logging
import ConfigParser

from requests import post as http_post
from sh import borg, hostname, mysqldump, rclone

log = logging.getLogger(os.path.splitext(__file__)[0])
log.setLevel(logging.INFO)
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(
    logging.Formatter('%(name)s [%(levelname)s]: %(message)s')
)
log.addHandler(_log_handler)
debug = True  # FIXME

HOSTNAME = hostname().strip()
ARCHIVE_PREFIX = HOSTNAME.strip()


def ensure_absolute_path(path):
    '''
    Make given path absolute anyway.
    '''
    return os.path.abspath(os.path.expanduser(path))


def new_backup_name():
    return '{}-{}'.format(
        ARCHIVE_PREFIX, datetime.utcnow().strftime('%Y%m%d%H%M%S')
    )


def load_configuration_file(location='~/.daily_backup.ini'):
    '''
    Load configuration from file. Configuration example:
    ```ini
    [mysql]
    databases=my_database
    directory=~/my_database_backup/
    defaults-extra-file=~/.my.conf

    [borg]
    repo=/home/user/my_borg_repo
    passphrase=my_borg_passphrase
    directories=~/my_database_backup
                ~/some_other_directory
    files=~/.vimrc
          ~/.zshrc
          /etc/some_config_file
    excludes=*.pyc
             *.swp

    [rclone]
    local_path=/home/user/my_borg_repo
    remote_path=dropbox:my_dropbox_folder_path

    [notification]
    eth0_pushcode=my_eth_pushcode
    ```
    '''
    location = ensure_absolute_path(location)
    section_requirements = {
        'mysql': ('directory', 'defaults-extra-file', ),
        'borg': ('passphrase', ),
        'rclone': ('local_path', 'remote_path', ),
        'notification': ('eth0_pushcode', ),
    }
    multivalue_options = {
        'mysql': ('databases', ),
        'borg': ('files', 'directories', 'excludes', ),
    }
    config = ConfigParser.SafeConfigParser()
    with io.open(location, encoding='utf-8') as rf:
        config.readfp(rf, location)
    # Check requirements of each section
    for section in section_requirements.keys():
        for option in section_requirements[section]:
            if not config.has_option(section, option):
                raise ValueError(
                    'Missing value for option {} in section {}'.format(
                        option, section
                    )
                )
    # Reform into dict
    result = {}
    for section in config.sections():
        section_data = {}
        for option in config.options(section):
            if option in multivalue_options.get(section, []):
                section_data[option] = config.get(section, option).splitlines()
            else:
                section_data[option] = config.get(section, option)
        result[section] = section_data
    return result


def backup_mysql_databases(extra_file, databases, directory):
    '''
    Backup specific MySQL / MariaDB databases using mysqldump.
    Dumped SQL files are placed into `directory`
     with the name of "${database}.sql", older dumps will be overwritten.
    Notice: ~/.my.conf MUST contains user & password for mysqldump to consume.
    '''
    if not isinstance(databases, (tuple, list, )):
        raise ValueError('`databases` must be of type `list` or `tuple`')

    directory = ensure_absolute_path(directory)
    extra_file = ensure_absolute_path(extra_file)
    log.info('Dumping databases into %s', directory)
    if not os.path.exists(directory):
        os.makedirs(directory)
    backup_results = []

    for database in databases:
        backup_location = os.path.join(directory, '{}.sql'.format(database))
        try:
            with io.open(backup_location, 'w', encoding='utf-8') as wf:
                mysqldump(
                    '--defaults-extra-file={}'.format(extra_file),
                    '--flush-logs', '--lock-tables', '--tz-utc',
                    '--databases', database,
                    _out=wf, _timeout=1800
                )
        except:
            log.error(
                'Failed to backup MySQL database %s', database, exc_info=True
            )
        else:
            log.info('Database %s dumped', database)
            backup_results.append(backup_location)

    return list(set(backup_results))


def create_borg_archive(
    borg_repo, archive_name, paths, excludes=None, passphrase=None
):
    '''
    Create new archive in given borg repo with given name.
    '''
    excludes = excludes or []

    paths = [ensure_absolute_path(p) for p in paths]
    paths = [p for p in paths if os.path.exists(p)]
    archive_name = '{}::{}'.format(borg_repo, archive_name)

    log.info(
        'Creating borg archive %s with %d direct items',
        archive_name, len(paths)
    )

    args = ['--stats', '--compression', 'zlib,5', archive_name, ]
    args.extend(paths)
    [args.extend(['--exclude', ex]) for ex in excludes]

    env = os.environ.copy()
    if passphrase is not None:
        env['BORG_PASSPHRASE'] = passphrase
    log.info(borg.create(*args, _env=env))
    return archive_name


def prune_borg_archives(borg_repo, prefix, passphrase=None):
    '''
    Prune given borg repo into containing:
    - 7 daily archives
    - 4 weekly archives
    - 6 monthly archives
    '''
    env = os.environ.copy()
    if passphrase is not None:
        env['BORG_PASSPHRASE'] = passphrase
    log.info('Pruning borg archives with prefix %s', prefix)
    log.info(
        borg.prune(
            '-v',
            borg_repo,
            '--prefix', prefix,
            '--keep-daily=7',
            '--keep-weekly=4',
            '--keep-monthly=6',
            _env=env
        )
    )


def sync_backup_archive(local_path, remote_path):
    '''
    Use rclone program to sync local backup files into cloud storage.
    rclone program MUST be configured properly before using this.
    '''
    local_path = ensure_absolute_path(local_path)
    log.info('Syncing %s to %s', local_path, remote_path)
    log.info(rclone.sync(local_path, remote_path))


def push_notification(push_code, text, prefix='*BackupBot*: '):
    '''
    Push a notification using the Telegram bot @eth0_bot.
    '''
    eth_endpoint = 'https://eth.api.mynook.info/push'
    text = prefix + text
    result = http_post(eth_endpoint, data={'text': text, 'code': push_code})
    return result.json().get('code', 204) == 200


def main():
    '''
    The main program workflow:
    1. load configuration file;
    2. (if enabled) dump MySQL / MariaDB databases;
    3. (if necessary) create new borg archive (results of step 2 will be included);
    4. (if configured) sync borg repo to cloud storage using rclone;
    5. (if configured) send a notification via Telegram bot @eth0_bot;

    All steps except the first can be skipped.
    '''
    try:
        config = load_configuration_file()
    except ValueError:
        log.error('Failed to load configuration file')
        sys.exit(1)

    # Extra items to be included in borg archive
    extra_paths = []

    archive_name = None
    # MySQL
    if 'mysql' in config:
        mysql = config['mysql']
        extra_paths.extend(
            backup_mysql_databases(
                mysql['defaults-extra-file'],
                mysql['databases'], mysql['directory']
            )
        )
    if 'borg' in config:
        borg_paths = extra_paths
        borg_paths.extend(config['borg']['directories'])
        borg_paths.extend(config['borg']['files'])

        archive_name = create_borg_archive(
            config['borg']['repo'],
            new_backup_name(),
            borg_paths,
            config['borg']['excludes'],
            config['borg']['passphrase']
        )
        prune_borg_archives(
            config['borg']['repo'],
            ARCHIVE_PREFIX,
            config['borg']['passphrase']
        )

    if 'rclone' in config:
        sync_backup_archive(
            config['rclone']['local_path'], config['rclone']['remote_path']
        )

    if archive_name and 'notification' in config:
        push_notification(
            config['notification']['eth0_pushcode'],
            '机器 `{}` 日常备份成功，存档名称 `{}`'.format(HOSTNAME, archive_name)
        )


if __name__ == '__main__':
    main()
