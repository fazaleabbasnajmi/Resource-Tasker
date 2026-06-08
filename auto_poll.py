#!/usr/bin/env python
"""
auto_poll.py  –  Background inbox poller for Resource Tasker
Runs mail_poll.sync_inbox() on a configurable interval.

Usage:
    python auto_poll.py              # polls every 5 minutes (default)
    POLL_INTERVAL=120 python auto_poll.py   # polls every 2 minutes

Environment variables (all also read by mail_poll.py):
    MAILBOX_USERNAME      Gmail address  (default: mentaccpssupport@gmail.com)
    MAILBOX_PASSWORD      Gmail App Password
    MAILBOX_HOST          IMAP host      (default: imap.gmail.com)
    MAILBOX_PORT          IMAP port      (default: 993)
    MAILBOX_USE_SSL       true/false     (default: true)
    MAILBOX_FOLDER        Mailbox folder (default: INBOX)
    POLL_INTERVAL         Seconds between polls (default: 300)
"""
import os
import sys
import time
import traceback

from mail_poll import sync_inbox

POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', '300'))


def main():
    print(f'Resource Tasker – Auto Email Poller')
    print(f'Inbox   : {os.environ.get("MAILBOX_USERNAME", "mentaccpssupport@gmail.com")}')
    print(f'Interval: every {POLL_INTERVAL}s')
    print('Press Ctrl+C to stop.\n')

    while True:
        try:
            sync_inbox()
        except RuntimeError as exc:
            print(f'[ERROR] {exc}', file=sys.stderr)
        except Exception:
            traceback.print_exc()

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()

