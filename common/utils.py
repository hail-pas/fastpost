import random
import string
from typing import List, Sequence
from email.message import EmailMessage
from email.mime.text import MIMEText

from pydantic import EmailStr
from aiosmtplib import SMTP

from fastpost.settings import get_settings

COMMON_TIME_STRING = "%Y-%m-%d %H:%M:%S"
COMMON_DATE_STRING = "%Y-%m-%d"


async def send_mail(to_mails: Sequence[EmailStr], text: str, subject: str, email_type: str):
    """
    发送邮件
    :param to_mails:
    :param text:
    :param subject:
    :param email_type:
    :return:
    """
    settings = get_settings()
    to_mails = to_mails
    text = text
    subject = subject
    client = SMTP(
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_TLS,
    )
    if email_type == "html":
        message = MIMEText(text, "html", "utf-8")
    else:
        message = EmailMessage()
        message.set_content(text)
    message["From"] = settings.EMAILS_FROM_EMAIL
    message["Subject"] = subject
    async with client:
        ret = await client.send_message(message, recipients=to_mails,)
    return ret


def join_params(
    params: dict,
    key: str = None,
    filter_none: bool = True,
    exclude_keys: List = None,
    sep: str = "&",
    reverse: bool = False,
    key_alias: str = "key",
):
    """
    字典排序拼接参数
    """
    tmp = []
    for p in sorted(params, reverse=reverse):
        value = params[p]
        if filter_none and value in [None, ""]:
            continue
        if exclude_keys:
            if p in exclude_keys:
                continue
        tmp.append("{0}={1}".format(p, value))
    if key:
        tmp.append("{0}={1}".format(key_alias, key))
    ret = sep.join(tmp)
    return ret


def generate_random_string(length: int, all_digits: bool = False, excludes: List = None):
    """
    生成任意长度字符串
    """
    if excludes is None:
        excludes = []
    if all_digits:
        all_char = string.digits
    else:
        all_char = string.ascii_letters + string.digits
    if excludes:
        for char in excludes:
            all_char.replace(char, "")
    return "".join(random.sample(all_char, length))
