from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from core import types
from utils import helpers

from appdata import shared


class Mail(metaclass=types.Singleton):
    __slots__ = ("context", "user", "port", "password", "_from", "host")

    def config(self, user: str, password: str, host: str, hostname: str, port: int):
        self.user = user
        self.password = password
        self.host = host
        self._from = "noreply@" + hostname
        self.port = port

    class __MailComposer:
        def __init__(self, outer: Mail, to: str, subject: str):
            self.outer = outer
            self.to = to
            self.subject = subject
            self.msg = MIMEMultipart("alternative")
            self._sent = False
            self._attached = False

        def __enter__(self):
            self.msg["From"] = self.outer._from
            self.msg["To"] = self.to
            self.msg["Subject"] = self.subject
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def attach_plain(self, part: str):
            self._attached = True
            self.msg.attach(MIMEText(part, "plain"))

        def attach_html(self, part: str):
            self._attached = True
            self.msg.attach(MIMEText(part, "html"))

        async def send(self) -> bool:
            if self._attached:
                raise RuntimeError("Nothing attached, maybe start composing?")
            if self._sent:
                raise RuntimeError("Email already sent")
            try:
                async with aiosmtplib.SMTP(
                    hostname=self.outer.host,
                    port=self.outer.port,
                    username=self.outer.user,
                    password=self.outer.password,
                    use_tls=True,
                    start_tls=True,
                ) as server:
                    await server.send_message(self.msg)
                self._sent = True
                return True
            except Exception as e:
                shared.print_err(e)
                return False

    def compose(self, to: str, subject: str):
        return self.__MailComposer(self, to, subject)

    async def send(self, to: str, subject: str, message: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from
            msg["To"] = to
            msg.attach(MIMEText(message, "plain"))
            # msg.attach(MIMEText(message, "plain")) # Attach html later?

            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=True,
                start_tls=True,
            ) as server:
                await server.send_message(msg)

            return True
        except Exception as e:
            shared.print_err(e)
        return False
