import httpx
import json
from typing import Optional
from config import config


class Notifier:
    def __init__(self):
        self.pusher_address = config.MessagePusherAddress
        self.pusher_token = config.MessagePusherToken
        self.smtp_server = config.SMTPServer
        self.smtp_account = config.SMTPAccount
        self.smtp_token = config.SMTPToken
        self.smtp_port = config.SMTPPort
        self.smtp_from = config.SMTPFrom
        self.root_email = config.RootUserEmail

    async def send_notification(self, subject: str, content: str, channel_id: int = None, channel_name: str = None) -> bool:
        if channel_id and channel_name:
            content = f"[Channel {channel_id} - {channel_name}] {content}"

        pusher_success = await self._send_to_pusher(subject, content)

        if self.root_email:
            email_success = await self._send_email(self.root_email, subject, content)
        else:
            email_success = True

        return pusher_success and email_success

    async def _send_to_pusher(self, subject: str, content: str) -> bool:
        if not self.pusher_address:
            return True

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "title": subject,
                    "content": content,
                    "template": "raw",
                }

                headers = {}
                if self.pusher_token:
                    headers["Authorization"] = f"Bearer {self.pusher_token}"

                response = await client.post(
                    self.pusher_address,
                    json=payload,
                    headers=headers,
                )

                return response.status_code == 200

        except Exception as e:
            print(f"Failed to send push notification: {e}")
            return False

    async def _send_email(self, to: str, subject: str, content: str) -> bool:
        if not self.smtp_server or not self.smtp_account or not self.smtp_token:
            return True

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.smtp_from or self.smtp_account
            msg["To"] = to
            msg["Subject"] = subject

            msg.attach(MIMEText(content, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_account, self.smtp_token)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    async def notify_channel_error(self, channel_id: int, channel_name: str, error: str):
        subject = f"Channel Error: {channel_name}"
        content = f"Channel {channel_id} ({channel_name}) encountered an error:\n\n{error}\n\nThe channel may have been automatically disabled."
        return await self.send_notification(subject, content, channel_id, channel_name)

    async def notify_channel_recovered(self, channel_id: int, channel_name: str):
        subject = f"Channel Recovered: {channel_name}"
        content = f"Channel {channel_id} ({channel_name}) has recovered and is now responding normally."
        return await self.send_notification(subject, content, channel_id, channel_name)

    async def notify_low_quota(self, user_id: int, username: str, remaining_quota: int):
        subject = f"Low Quota Warning"
        content = f"User {username} (ID: {user_id}) has low remaining quota: {remaining_quota}"
        return await self.send_notification(subject, content)

    async def notify_channel_auto_disabled(self, channel_id: int, channel_name: str, reason: str):
        subject = f"Channel Auto-Disabled: {channel_name}"
        content = f"Channel {channel_id} ({channel_name}) has been automatically disabled.\n\nReason: {reason}"
        return await self.send_notification(subject, content, channel_id, channel_name)


notifier = Notifier()


async def send_notification(subject: str, content: str, channel_id: int = None, channel_name: str = None) -> bool:
    return await notifier.send_notification(subject, content, channel_id, channel_name)


async def notify_channel_error(channel_id: int, channel_name: str, error: str):
    return await notifier.notify_channel_error(channel_id, channel_name, error)


async def notify_channel_recovered(channel_id: int, channel_name: str):
    return await notifier.notify_channel_recovered(channel_id, channel_name)


async def notify_low_quota(user_id: int, username: str, remaining_quota: int):
    return await notifier.notify_low_quota(user_id, username, remaining_quota)


async def notify_channel_auto_disabled(channel_id: int, channel_name: str, reason: str):
    return await notifier.notify_channel_auto_disabled(channel_id, channel_name, reason)