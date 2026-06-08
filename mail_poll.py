import email
import imaplib
import os
from email.header import decode_header, make_header

from app import create_app
from routes.email_intake import create_task_from_email, is_actionable_subject

DEFAULT_IMAP_HOST = 'imap.gmail.com'
DEFAULT_IMAP_PORT = 993


def decode_text(value):
    if not value:
        return ''
    return str(make_header(decode_header(value)))


def extract_text_from_message(message):
    plain_parts = []
    html_parts = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = (part.get('Content-Disposition') or '').lower()
            if 'attachment' in disposition:
                continue
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            if not payload:
                continue
            text = payload.decode(charset, errors='replace')
            if content_type == 'text/plain':
                plain_parts.append(text)
            elif content_type == 'text/html':
                html_parts.append(text)
    else:
        payload = message.get_payload(decode=True)
        charset = message.get_content_charset() or 'utf-8'
        if payload:
            text = payload.decode(charset, errors='replace')
            if message.get_content_type() == 'text/html':
                html_parts.append(text)
            else:
                plain_parts.append(text)

    return '\n'.join(plain_parts).strip(), '\n'.join(html_parts).strip()


def sync_inbox():
    username = os.environ.get('MAILBOX_USERNAME', 'mentaccpssupport@gmail.com')
    password = os.environ.get('MAILBOX_PASSWORD') or os.environ.get('MAILBOX_APP_PASSWORD')
    host = os.environ.get('MAILBOX_HOST', DEFAULT_IMAP_HOST)
    port = int(os.environ.get('MAILBOX_PORT', str(DEFAULT_IMAP_PORT)))
    use_ssl = os.environ.get('MAILBOX_USE_SSL', 'true').lower() not in {'0', 'false', 'no'}
    mailbox = os.environ.get('MAILBOX_FOLDER', 'INBOX')

    if not password:
        raise RuntimeError('MAILBOX_PASSWORD is required to poll the mailbox over IMAP.')

    app = create_app()
    with app.app_context():
        client = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
        try:
            client.login(username, password)
        except imaplib.IMAP4.error as exc:
            if 'gmail.com' in username.lower() or 'google' in host.lower() or host == DEFAULT_IMAP_HOST:
                raise RuntimeError(
                    f'Unable to authenticate to Gmail for {username}. '
                    'Google does not allow normal account passwords for IMAP access here. '
                    'Use a Gmail App Password, not the normal account password. '
                    'Also confirm 2-Step Verification is enabled on the Google account and IMAP access is available. '
                    'Set MAILBOX_PASSWORD (or MAILBOX_APP_PASSWORD) to the generated app password and try again.'
                ) from exc

            raise RuntimeError(
                f'Unable to authenticate to IMAP server {host}:{port} for {username}. '
                'Verify MAILBOX_USERNAME, MAILBOX_PASSWORD, MAILBOX_HOST, MAILBOX_PORT, and MAILBOX_USE_SSL.'
            ) from exc
        client.select(mailbox)

        status, data = client.search(None, '(UNSEEN)')
        if status != 'OK':
            raise RuntimeError('Unable to search mailbox for unread messages.')

        message_ids = data[0].split()
        created = 0
        existing = 0
        skipped = 0

        for message_num in message_ids:
            status, fetched = client.fetch(message_num, '(RFC822)')
            if status != 'OK':
                continue

            raw_email = fetched[0][1]
            message = email.message_from_bytes(raw_email)
            subject = decode_text(message.get('Subject')) or ''
            sender = decode_text(message.get('From'))
            message_id = decode_text(message.get('Message-ID'))
            text_body, html_body = extract_text_from_message(message)

            # Skip emails that don't start with a trigger word.
            if not is_actionable_subject(subject):
                print(f'  Skipped (subject filter): "{subject}" from {sender}')
                skipped += 1
                # Mark as read so it's not re-checked next run.
                client.store(message_num, '+FLAGS', '\\Seen')
                continue

            task, was_created, error = create_task_from_email({
                'from': sender,
                'subject': subject,
                'text': text_body,
                'html': html_body,
                'message_id': message_id,
            })
            if error:
                continue

            if was_created:
                created += 1
            else:
                existing += 1

            client.store(message_num, '+FLAGS', '\\Seen')

        client.logout()
        print(f'Synced inbox {username}: created={created}, existing={existing}, skipped={skipped}, unread_checked={len(message_ids)}')


if __name__ == '__main__':
    sync_inbox()

