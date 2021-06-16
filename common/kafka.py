import json
import asyncio
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from fastpost.settings import get_settings

loop = asyncio.get_event_loop()

logger = logging.getLogger(__name__)


class MyKafka:
    def __init__(self):
        self._producer = None
        self._consumer = None

    async def get_producer(self):
        if not self._producer:
            self._producer = AIOKafkaProducer(loop=loop, bootstrap_servers=get_settings().KAFKA_BOOTSTRAP_SERVERS)
            await self._producer.start()
        return self._producer

    async def get_consumer(self, topic: str, group_id: str):
        if not self._consumer:
            self._consumer = AIOKafkaConsumer(
                topic, loop=loop, group_id=group_id, bootstrap_servers=get_settings().KAFKA_BOOTSTRAP_SERVERS,
            )
            await self._consumer.start()
        return self._consumer

    async def send(self, data, topic: str):
        producer = await self.get_producer()
        await producer.send(topic, json.dumps(data))


kafka = MyKafka()
