#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
sshd notification script to be used with PAM sshd module.
'''
import ConfigParser
import io
import os

from requests import post as http_post
from sh import hostname

HOSTNAME = hostname().strip()
ACTION_TYPES = {
    'open_session': '登录',
    'close_session': '注销登录',
}


def load_config():
    '''
    Read config file from /etc/eth0_common.ini
    Config Sample:
    ```ini
    [eth0_bot]
    push_code=xxxxxx
    [PAM]
    ignore_users=git
                 me
    ignore_actions=close_session
    ```
    '''
    CONFIG_FILE = '/etc/eth0_common.ini'
    data = {}
    multivalue_options = {
        'eth0_bot': tuple(),
        'PAM': ('ignore_users', 'ignore_actions', ),
    }
    section_requirements = {
        'eth0_bot': ('push_code', ),
        'PAM': tuple(),
    }

    config = ConfigParser.RawConfigParser()
    with io.open(CONFIG_FILE, encoding='utf-8') as rf:
        config.readfp(rf)

    for section in section_requirements.keys():
        data[section] = {}
        for option in section_requirements[section]:
            if config.has_option(section, option):
                data[section][option] = config.get(section, option)
            else:
                data[section][option] = ''

    for section in config.sections():
        section_data = {}
        for option in config.options(section):
            if option in multivalue_options.get(section, []):
                section_data[option] = config.get(section, option).splitlines()
            else:
                section_data[option] = config.get(section, option)
        data[section] = section_data

    return data


def push_notification(s, code, server='https://eth.api.mynook.info/push'):
    '''
    Push text `s` with given `code`.
    '''
    http_post(
        server,
        data={
            'code': code,
            'text': s,
        },
        timeout=30
    )


def pam_filter(user, action, config):
    '''
    Filter given user.action pair with given config.
    If config contains ignore_*, we return False,
    thus no notification will be pushed.
    '''
    if user in config.get('PAM', {}).get('ignore_users', []):
        return False
    if action in config.get('PAM', {}).get('ignore_actions', []):
        return False
    return True


def main():
    config = load_config()
    user = os.environ['PAM_USER']
    action = os.environ['PAM_TYPE']
    if pam_filter(user, action, config):
        push_notification(
            (
                '*PAMBot*:\n'
                '*{service}*: '
                '用户 `{user}` 从 {ip} 在服务器 `{hostname}` 上 *{action}*'
            ).format(
                service=os.environ['PAM_SERVICE'],
                user=user,
                ip=os.environ['PAM_RHOST'],
                hostname=HOSTNAME,
                action=ACTION_TYPES.get(action, action)
            ),
            config['eth0_bot']['push_code']
        )


if __name__ == '__main__':
    main()
