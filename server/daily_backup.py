#!/usr/bin/env python2
# coding: utf-8
'''
A daily backup script
How to use:
0. Init a borg repository using `borg init ...`
1. Fill information in this script
2. Set a daily cron job for this script
3. Sleep. :) You'll be notified once the backup finished or failed.
'''
import os

from requests import post as http_post
from sh import borg, hostname, date

# Please init before using this script
# `borg init ...`
BORG_REPOSITORY = '/your/borg/repo/name'
# Get a push code following this: https://jokerqyou.github.io/ethbot
PUSH_CODE = 'xxxxxx'
# Add the directories you want to backup
DIRECTORIES = (
    '/important/data',
    '/home/user/secret/data',
)
# Add the directories or patterns you want to exclude
EXCLUDES = (
    '*.pyc',
    '*.swp',
    '/i/dont/care/about/this/data',
    '/home/Ben/Music/Justin\ Bieber',
)
HOSTNAME = hostname().strip()
DATE = date('+%Y-%m-%d').strip()


def backup(*directories, **kwargs):
    '''
    Backup a directory using borg
    '''
    directories = [d for d in directories if os.path.exists(d)]
    repository = '{}::{}-{}'.format(BORG_REPOSITORY, HOSTNAME, DATE)
    excludes = kwargs.pop('excludes', [])
    excludes = [excludes, ]\
        if not isinstance(excludes, (list, tuple, ))\
        else excludes
    arguments = ['--stats', '--compression', 'zlib,5', repository, ]
    arguments.extend(directories)
    [arguments.extend(['--exclude', ex]) for ex in excludes]
    borg.create(arguments)


def push_notification(s):
    '''
    Push a notification via Telegram bot
    '''
    http_post(
        'https://eth.api.mynook.info/push',
        data={
            'code': PUSH_CODE,
            'text': s,
        }
    )


def prune():
    '''
    Prune backups to maintain 7 daily,
    4 weekly and 6 monthly archives of THIS machine
    '''
    prefix = '{}-'.format(HOSTNAME)
    borg.prune(
        '-v',
        BORG_REPOSITORY,
        '--prefix', prefix,
        '--keep-daily=7',
        '--keep-weekly=4',
        '--keep-monthly=6'
    )


def main():
    try:
        backup_name = '{}-{}'.format(HOSTNAME, DATE)
        backup(*DIRECTORIES, excludes=EXCLUDES)
    except Exception as e:
        push_notification(u'每日备份失败，错误原因：`{}`'.format(e))
    else:
        push_notification(
            u'每日备份成功，存档名称：`{}::{}`'.format(BORG_REPOSITORY, backup_name)
        )


if __name__ == '__main__':
    main()
