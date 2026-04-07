import logging
import msgpack
from aiokafka import AIOKafkaProducer
from app.config import settings

log = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None

async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BROKER,
            value_serializer=lambda m: msgpack.packb(m)
        )
        try:
            await _producer.start()
            log.info("Connected to Kafka: %s", settings.KAFKA_BROKER)
        except Exception as e:
            log.error("Failed to connect to Kafka: %s", e)
            _producer = None
            raise e
    return _producer

async def publish_states(entities: list[dict]) -> None:
    if not entities:
        return
    try:
        producer = await get_producer()
        # Publish exactly what the collector expects
        data = {"upsert": entities}
        await producer.send_and_wait(settings.KAFKA_TOPIC_AIRCRAFT, data)
    except Exception as exc:
        log.error("Kafka publish error: %s", exc)

async def close_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
