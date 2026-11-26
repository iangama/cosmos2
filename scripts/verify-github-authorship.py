"""Reject an incorrect identity before committing or publishing this source backup."""
import argparse
import json
import re
import subprocess
import sys

NAME = 'Ian'
EMAIL = '113548582+iangama@users.noreply.github.com'


def git(*args):
    return subprocess.check_output(['git', *args], text=True, encoding='utf8').strip()


def pending():
    for role in ['AUTHOR', 'COMMITTER']:
        identity = git('var', 'GIT_' + role + '_IDENT')
        match = re.fullmatch(r'(.+) <([^<>]+)> \d+ [+-]\d{4}', identity)
        if not match or match.groups() != (NAME, EMAIL):
            raise ValueError('Identidade Git incorreta para ' + role + '; configure Ian e ' + EMAIL)


def history(revision):
    log = git('log', '--format=%H%x09%an%x09%ae%x09%cn%x09%ce', revision, '--')
    count = 0
    for row in log.splitlines():
        commit, author, author_email, committer, committer_email = row.split('\t')
        if (author, author_email, committer, committer_email) != (NAME, EMAIL, NAME, EMAIL):
            raise ValueError('Autoria inesperada no commit ' + commit + '; envio interrompido.')
        count += 1
    if not count:
        raise ValueError('Nenhum commit verificado.')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--pending', action='store_true')
    modes.add_argument('--history', nargs='?', const='HEAD', metavar='REVISION')
    modes.add_argument('--pre-push', action='store_true')
    args = parser.parse_args()
    count = 0
    if args.pending:
        pending()
    elif args.history:
        count = history(args.history)
    else:
        for row in sys.stdin:
            _, local_sha, _, _ = row.split()
            if set(local_sha) != {'0'}:
                count += history(local_sha)
    print(json.dumps(dict(accepted=True, commits_checked=count, author=NAME, email=EMAIL)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
