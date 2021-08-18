from elasticsearch import AsyncElasticsearch
from elasticsearch_dsl import Document


class BaseModel(Document):
    pass


BaseModel.init()

es = AsyncElasticsearch()
