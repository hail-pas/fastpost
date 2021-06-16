import aioredis
from aioredis import Redis

from fastpost.settings import get_settings


class AsyncRedisUtil:
    """
    异步redis操作
    """

    _pool = None  # type:Redis

    @classmethod
    async def init(
        cls,
        host=get_settings().REDIS_HOST,
        port=get_settings().REDIS_PORT,
        password=get_settings().REDIS_PASSWORD,
        db=0,
        **kwargs,
    ):
        cls._pool = await aioredis.create_redis_pool(f"redis://{host}:{port}", password=password, db=db, **kwargs)
        return cls._pool

    @classmethod
    async def get_pool(cls):
        assert cls._pool, "must call init first"
        return cls._pool

    @classmethod
    async def _exp_of_none(cls, *args, exp_of_none, callback):
        if not exp_of_none:
            return await getattr(cls._pool, callback)(*args)
        key = args[0]
        tr = cls._pool.multi_exec()
        fun = getattr(tr, callback)
        exists = await cls._pool.exists(key)
        if not exists:
            fun(*args)
            tr.expire(key, exp_of_none)
            ret, _ = await tr.execute()
        else:
            fun(*args)
            ret = (await tr.execute())[0]
        return ret

    @classmethod
    async def set(cls, key, value, exp=None):
        assert cls._pool, "must call init first"
        await cls._pool.set(key, value, expire=exp)

    @classmethod
    async def get(cls, key, default=None):
        assert cls._pool, "must call init first"
        value = await cls._pool.get(key)
        if value is None:
            return default
        return value

    @classmethod
    async def hget(cls, name, key, default=0):
        """
        缓存清除，接收list or str
        """
        assert cls._pool, "must call init first"
        v = await cls._pool.hget(name, key)
        if v is None:
            return default
        return v

    @classmethod
    async def get_or_set(cls, key, default=None, value_fun=None):
        """
        获取或者设置缓存
        """
        assert cls._pool, "must call init first"
        value = await cls._pool.get(key)
        if value is None and default:
            return default
        if value is not None:
            return value
        if value_fun:
            value, exp = await value_fun()
            await cls._pool.set(key, value, expire=exp)
        return value

    @classmethod
    async def delete(cls, key):
        """
        缓存清除，接收list or str
        """
        assert cls._pool, "must call init first"
        return await cls._pool.delete(key)

    @classmethod
    async def sadd(cls, name, values, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, values, exp_of_none=exp_of_none, callback="sadd")

    @classmethod
    async def hset(cls, name, key, value, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hset")

    @classmethod
    async def hincrby(cls, name, key, value=1, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrby")

    @classmethod
    async def hincrbyfloat(cls, name, key, value, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrbyfloat")

    @classmethod
    async def incrby(cls, name, value=1, exp_of_none=None):
        assert cls._pool, "must call init first"
        return await cls._exp_of_none(name, value, exp_of_none=exp_of_none, callback="incrby")

    @classmethod
    async def close(cls):
        cls._pool.close()
        await cls._pool.wait_closed()
