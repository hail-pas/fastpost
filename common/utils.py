import os
import sys
import random
import string
import threading
from typing import List, Union, Sequence
from asyncio import sleep
from datetime import datetime
from functools import wraps
from contextlib import asynccontextmanager
from collections import namedtuple
from email.message import EmailMessage
from email.mime.text import MIMEText

import pytz
from pydantic import EmailStr
from aiosmtplib import SMTP
from starlette.requests import Request

from db.redis import get_async_redis
from core.settings import settings

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


def get_client_ip(request: Request):
    """
    获取客户端真实ip
    :param request:
    :return:
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host


def partial(func, *args):
    def new_func(*fargs):
        return func(*(args + fargs))

    new_func.func = func
    new_func.args = args
    return new_func


# datetime util
def datetime_now():
    if os.environ.get("USE_TZ") == "True":
        return datetime.now(tz=pytz.utc)
    else:
        return datetime.now(pytz.timezone(os.environ.get("TIMEZONE") or "UTC"))


def timelimit(timeout: int):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>>
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        RuntimeError: took too long
        >>> timelimit(1)(meaningoflife)()
        42
    _Caveat:_ The function isn't stopped after `timeout` seconds but continues
    executing in a separate thread. (There seems to be no way to kill a thread.)
    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """

    def _1(function):
        @wraps(function)
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except Exception:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.is_alive():
                raise RuntimeError("took too long")
            if c.error:
                raise c.error[1]
            return c.result

        return _2

    return _1


def commify(n: Union[int, float]):
    """
    Add commas to an integer `n`.
        >>> commify(1)
        '1'
        >>> commify(123)
        '123'
        >>> commify(-123)
        '-123'
        >>> commify(1234)
        '1,234'
        >>> commify(1234567890)
        '1,234,567,890'
        >>> commify(123.0)
        '123.0'
        >>> commify(1234.5)
        '1,234.5'
        >>> commify(1234.56789)
        '1,234.56789'
        >>> commify(' %.2f ' % -1234.5)
        '-1,234.50'
        >>> commify(None)
        >>>
    """
    if n is None:
        return None

    n = str(n).strip()

    if n.startswith("-"):
        prefix = "-"
        n = n[1:].strip()
    else:
        prefix = ""

    if "." in n:
        dollars, cents = n.split(".")
    else:
        dollars, cents = n, None

    r = []
    for i, c in enumerate(str(dollars)[::-1]):
        if i and (not (i % 3)):
            r.insert(0, ",")
        r.insert(0, c)
    out = "".join(r)
    if cents:
        out += "." + cents
    return prefix + out


RedisLock = namedtuple("RedisLock", ["lock"])


def make_redis_lock(get_redis):
    redis = None

    async def get_redis_():
        nonlocal redis

        if redis is None:
            redis = await get_redis()

        return redis

    @asynccontextmanager
    async def lock(key, timeout=60):
        r = await get_redis_()
        v = os.urandom(20)

        accuired = False

        while not accuired:
            accuired = await r.set(key, v, expire=timeout, exist="SET_IF_NOT_EXIST")

            if not accuired:
                await sleep(1)

        try:
            yield
        finally:
            await r.eval(
                """
                if redis.call("get", KEYS[1]) == ARGV[1]
                then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            """,
                [key],
                [v],
            )

    _redis_lock = RedisLock(lock=lock,)

    return _redis_lock


redis_lock = make_redis_lock(get_async_redis)  # redis lock in async context
"""
async with redis_lock.lock(keys.RedisCacheKey.redis_lock.format("name")):
    pass
"""
