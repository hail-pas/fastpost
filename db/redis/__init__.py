import redis as o_redis
import aioredis

from core.settings import settings


class AsyncRedisUtil:
    """
    异步redis操作
    """

    _pool = None

    @classmethod
    async def init(
        cls, host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=0, **kwargs,
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


class RedisUtil:
    """
    同步Redis操作
    """

    r = None

    @classmethod
    def init(
        cls, host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=0, **kwargs,
    ):
        pool = o_redis.ConnectionPool(host=host, port=port, password=password, db=db, **kwargs)
        cls.r = o_redis.Redis(connection_pool=pool)  # type:o_redis.Redis

    @classmethod
    async def get_pool(cls):
        assert cls.r, "must call init first"
        return cls.r

    @classmethod
    def _exp_of_none(cls, *args, exp_of_none, callback):
        if not exp_of_none:
            return getattr(cls.r, callback)(*args)
        with cls.r.pipeline() as pipe:
            count = 0
            while True:
                try:
                    fun = getattr(pipe, callback)
                    key = args[0]
                    pipe.watch(key)
                    exp = pipe.ttl(key)
                    pipe.multi()
                    if exp == -2:
                        fun(*args)
                        pipe.expire(key, exp_of_none)
                        ret, _ = pipe.execute()
                    else:
                        fun(*args)
                        ret = pipe.execute()[0]
                    return ret
                except o_redis.WatchError:
                    if count > 3:
                        raise o_redis.WatchError
                    count += 1
                    continue

    @classmethod
    def get_or_set(cls, key, default=None, value_fun=None):
        """
        获取或者设置缓存
        """
        value = cls.r.get(key)
        if value is None and default:
            return default
        if value is not None:
            return value
        if value_fun:
            value, exp = value_fun()
            cls.r.set(key, value, exp)
        return value

    @classmethod
    def get(cls, key, default=None):
        value = cls.r.get(key)
        if value is None:
            return default
        return value

    @classmethod
    def set(cls, key, value, exp=None):
        """
        设置缓存
        """
        return cls.r.set(key, value, exp)

    @classmethod
    def delete(cls, key):
        """
        缓存清除，接收list or str
        """
        return cls.r.delete(key)

    @classmethod
    def sadd(cls, name, values, exp_of_none=None):
        return cls._exp_of_none(name, values, exp_of_none=exp_of_none, callback="sadd")

    @classmethod
    def hset(cls, name, key, value, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hset")

    @classmethod
    def hincrby(cls, name, key, value=1, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrby")

    @classmethod
    def hincrbyfloat(cls, name, key, value, exp_of_none=None):
        return cls._exp_of_none(name, key, value, exp_of_none=exp_of_none, callback="hincrbyfloat")

    @classmethod
    def incrby(cls, name, value=1, exp_of_none=None):
        return cls._exp_of_none(name, value, exp_of_none=exp_of_none, callback="incrby")

    @classmethod
    def hget(cls, name, key, default=None):
        """
        缓存清除，接收list or str
        """
        v = cls.r.hget(name, key)
        if v is None:
            return default
        return v


async def get_async_redis():
    return AsyncRedisUtil.get_pool()


def get_sync_redis():
    return RedisUtil.get_pool()
