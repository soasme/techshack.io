#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re
import argparse
import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from uuid import uuid4

ROW_TEMPLATE = """<article class="post" id="%(uuid)s">
    <div class="post-content"><p>%(thoughts)s</p></div>
    <div class="post-permalink"><a class="btn btn-default read-original" href="%(ref_url)s">Read Original Post</a></div>
    <footer class="post-footer clearfix">
        <div class="pull-left tag-list">%(tags)s</div>
    </footer>
</article>"""

SITE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="%(description)s">
    <meta name="author" content="%(author)s">
    <title>%(title)s</title>
    <link href="https://cdn.bootcss.com/bootstrap/3.3.7/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; padding-bottom: 20px; }
        .header, .marketing, .footer { padding-right: 15px; padding-left: 15px; }
        .header { padding-bottom: 20px; border-bottom: 1px solid #e5e5e5; }
        .header h3 { margin-top: 0; margin-bottom: 0; line-height: 40px; }
        .nav-pills>li.active>a, .nav-pills>li.active>a:focus, .nav-pills>li.active>a:hover { background-color: #20b2aa; }
        .footer { padding-top: 19px; color: #777; border-top: 1px solid #e5e5e5; }
        @media (min-width: 768px) { .container { max-width: 730px; } }
        .container-narrow > hr { margin: 30px 0; }
        .jumbotron { text-align: center; border-bottom: 1px solid #e5e5e5; }
        .jumbotron .btn { padding: 14px 24px; font-size: 21px; background-color: #20b2aa; }
        .jumbotron .logo { width: 100%%; }
        .post { padding: 0 35px; background: #ffffff; margin-bottom: 15px; position: relative; overflow: hidden; }
        .post .label-default { margin: 2px; }
        .post .post-content { margin: 30px 0; }
        .post-content { font: 400 18px/1.62 "Georgia", "Xin Gothic", "Hiragino Sans GB", "Droid Sans Fallback", "Microsoft YaHei", sans-serif; color: #444443; }
        .post-content p { margin-top: 0; margin-bottom: 1.46em; }
        .post-permalink .read-original { border: 1px solid #20b2aa; background: #20b2aa; color: #ffffff; transition: all 0.2s ease-in-out; border-radius: 5px; }
        .post .post-footer { border-bottom: 1px solid #ebebeb; padding: 10px 0 0; }
        .post .post-footer .tag-list { color: #959595; line-height: 28px; }
        .post .post-footer .tag-list  a { color: #959595; margin-left: 7px; }
        @media screen and (min-width: 768px) {
            .header, .marketing, .footer { padding-right: 0; padding-left: 0; }
            .header { margin-bottom: 30px; }
            .jumbotron { border-bottom: 0; }
        }
    </style>
    <!--[if lt IE 9]>
      <script src="https://cdn.bootcss.com/html5shiv/3.7.3/html5shiv.min.js"></script>
      <script src="https://cdn.bootcss.com/respond.js/1.4.2/respond.min.js"></script>
    <![endif]-->
    </head>
    <body>
        <div class="container">
            <div class="header clearfix">
                <nav>
                    <ul class="nav nav-pills pull-right">
                        <li role="presentation" class="active"><a href="/">Home</a></li>
                    </ul>
                </nav>
                <h3 class="text-muted">%(program_name)s</h3>
            </div>
            <div class="jumbotron">
                <h1><img class="logo" src="./static/tech-shack.png"></h1>
                <p class="lead">%(jumbotron_text)s</p>
                <!-- <p><a class="btn btn-lg btn-success" href="#" role="button">Subscribe</a></p> -->
            </div>
            <div class="row">
                %(posts)s
            </div>
            <footer class="footer">
                <p>&copy; 2017 Ju Lin.</p>
            </footer>
        </div>
</html>"""

def prepare_database(conn):
    """Create tables."""
    cursor = conn.cursor()
    cursor.execute("create table if not exists stanza (id text primary key, created text, ref text, thoughts text, tags text)")
    conn.commit()


@contextmanager
def open_database():
    """
    * ENV required: `STANZA_FILE_PATH`.

    with open_database() as conn:
        do_something(conn)
    """
    path = os.environ.get('STANZA_FILE_PATH')
    conn = sqlite3.connect(path)
    prepare_database(conn)
    try:
        yield conn
    finally:
        conn.close()


def get_stanzas(conn):
    cursor = conn.cursor()
    cursor.execute("select * from stanza order by created desc")
    seg = []
    for stanza in cursor:
        if not seg or seg[-1][1][:9] == stanza[1][:9]:
            seg.append(stanza)
        else:
            yield seg
            seg = [stanza]
    if seg:
        yield seg




def get_stanza(conn, uuid):
    cursor = conn.cursor()
    cursor.execute("select * from stanza where id=?", (uuid, ))
    return cursor.fetchone()


def create_stanza(conn, ref):
    cursor = conn.cursor()
    uuid = str(uuid4())
    created = datetime.utcnow().isoformat() + '+0000'
    cursor.execute("insert into stanza(id,created,ref) values(?,?,?)", (uuid, created, ref, ))
    conn.commit()
    return uuid


def set_stanza_thoughts(conn, uuid, thoughts):
    cursor = conn.cursor()
    cursor.execute("update stanza set thoughts=? where id=?", (thoughts, uuid, ))
    conn.commit()


def set_stanza_tags(conn, uuid, tags):
    cursor = conn.cursor()
    tags = tags.replace(',', '|')
    cursor.execute("update stanza set tags=? where id=?", (tags, uuid, ))
    conn.commit()


def format_stanza(stanza):
    return """uuid: %s
created: %s
ref: %s
thoughts: %s
tags: %s""" % tuple(stanza)


def start_stanza_session(uuid):
    with open('/tmp/techshack.io.stanza.session', 'w') as f:
        f.write(uuid)


def destroy_stanza_session():
    if os.path.exists('/tmp/techshack.io.stanza.session'):
        os.remove('/tmp/techshack.io.stanza.session')


def get_stanza_session():
    if os.path.exists('/tmp/techshack.io.stanza.session'):
        with open('/tmp/techshack.io.stanza.session', 'r') as f:
            return f.read()



def prog_slackbot(args, options):
    """Run slackbot.

    * ENV required: `SLACKBOT_API_TOKEN`.

    """
    from slackbot.bot import Bot
    from slackbot.bot import respond_to
    import re
    import json

    @respond_to('ping', re.IGNORECASE)
    def respond_to_github(message):
        message.reply('pong')

    @respond_to('show stanza (.*)', re.IGNORECASE)
    def show_stanza(message, uuid):
        with open_database() as conn:
            stanza = get_stanza(conn, uuid)
            if not stanza:
                message.reply('stanza %s not found' % uuid)
            else:
                message.reply(format_stanza(stanza))

    @respond_to('save stanza (.*)', re.IGNORECASE)
    def save_stanza_to_dat(message, url):
        with open_database() as conn:
            uuid = create_stanza(conn, url)
            start_stanza_session(uuid)
            message.reply('Start editing %s' % uuid)

    @respond_to('edit stanza (.*)', re.IGNORECASE)
    def edit_stanza(message, uuid):
        with open_database() as conn:
            if get_stanza(conn, uuid):
                start_stanza_session(uuid)
                message.reply('Start editing %s' % uuid)
            else:
                message.reply('Stanza %s not found' % uuid)

    @respond_to('done stanza')
    def stop_editing_stanza(message):
        with open_database() as conn:
            uuid = get_stanza_session()
            if uuid:
                destroy_stanza_session()
                message.reply('Quit editing %s' % uuid)
                message.reply(format_stanza(get_stanza(conn, uuid)))
            else:
                message.reply('No session found.')

    @respond_to('thoughts (.*)')
    def set_stanza_thoughts_to_dat(message, thoughts):
        with open_database() as conn:
            uuid = get_stanza_session()
            if uuid:
                stanza = get_stanza(conn, uuid)
                if stanza:
                    set_stanza_thoughts(conn, uuid, thoughts)
                    message.reply('Done')
                else:
                    destroy_stanza_session()
                    message.reply('Stanza %s not found' % uuid)
            else:
                message.reply('No session found.')

    @respond_to('tags (.*)')
    def set_stanza_tags_to_dat(message, tags):
        with open_database() as conn:
            uuid = get_stanza_session()
            if uuid:
                stanza = get_stanza(conn, uuid)
                if stanza:
                    set_stanza_tags(conn, uuid, tags)
                    message.reply('Done')
                else:
                    destroy_stanza_session()
                    message.reply('Stanza %s not found' % uuid)
            else:
                message.reply('No session found.')


    bot = Bot()
    bot.run()

def prog_publish(args, options):
    """Publish stanzas as static website."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', help='path to dest directory.', required=True)
    parser.add_argument('--before-days', '-B', help='Before days', type=int, default=1)
    parser.add_argument('--after-days', '-A', help='After days', type=int, default=0)
    args = parser.parse_args(options)
    with open_database() as conn:
        index = 1
        for stanzas in get_stanzas(conn):
            widgets = []
            for stanza in stanzas:
                uuid, created, ref, thoughts, tags = stanza
                ref_url = ref[1:-1] if ref.startswith('<') and ref.endswith('>') else '#'
                thoughts = re.sub(r'<(.*)>', r'<a href="\1">\1</a>', thoughts)
                thoughts = thoughts.replace(r'\n', '<br>')
                tags = ''.join(['<span class="label label-default">%s</span>' % tag for tag in tags.split('|') if tag])
                widget = ROW_TEMPLATE % dict(uuid=uuid, thoughts=thoughts, ref_url=ref_url, tags=tags)
                widgets.append(widget)

            page = SITE_TEMPLATE % dict(title='Tech Shack',
                description='Share useful technical posts for backend engineers.',
                author='Ju Lin <soasme@gmail.com>',
                program_name="Tech Shack",
                jumbotron_text="Share useful technical posts for backend engineers.",
                posts=''.join(widgets),
            )

            with open(os.path.join(args.dest, 'archive-%d.html' % index), 'w') as f:
                f.write(page)

            if index == 1:
                with open(os.path.join(args.dest, 'index.html'), 'w') as f:
                    f.write(page)

            index += 1

def prog_zen(args, options):
    """Print zen of this project."""
    print('Automate myself, and gain knowledge.')


def find_prog(prog):
    """Find prog function by parameter [prog]."""
    try:
        return globals()['prog_%s' % prog]
    except KeyError:
        raise Exception('Prog %s not found' % prog)


def main():
    """Main entry.

    Support multiple level prog.

        $ python techshack.py zen
        $ python techshack.py zen unknown -n
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('prog', help='program', nargs='+')
    args, unknown = parser.parse_known_args()
    prog_name = args.prog[0]
    prog = find_prog(prog_name)
    prog(args.prog[1:], unknown)


if __name__ == '__main__':
    main()
