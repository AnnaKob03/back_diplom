from fastapi import FastAPI, HTTPException
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Query
from elasticsearch import Elasticsearch


# Загрузка переменных окружения
load_dotenv()
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")

app = FastAPI()

# Подключение к Elasticsearch
es = Elasticsearch(ELASTICSEARCH_URL)

@app.on_event("startup")
def check_elasticsearch():
    if not es.ping():
        raise HTTPException(status_code=500, detail="Elasticsearch is not reachable.")

@app.get("/health")
def health_check():
    if es.ping():
        return {"status": "Elasticsearch is reachable"}
    else:
        raise HTTPException(status_code=500, detail="Elasticsearch is not reachable")

@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI application!"}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("favicon.ico")


from fastapi import FastAPI, HTTPException, Query
from elasticsearch import Elasticsearch

app = FastAPI()

# Подключение к Elasticsearch
es = Elasticsearch("http://localhost:9200")


@app.get("/search")
def search_articles(
    query: str = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    size: int = Query(100, ge=1, le=1000, description="Number of results per page (max 1000)")
):
    """
    Поиск статей по запросу с поддержкой пагинации
    """
    try:
        # Если запрос пустой, возвращаем все данные
        if not query:
            search_query = {
                "query": {
                    "match_all": {}
                }
            }
        else:
            # Формируем запрос для поиска по ключевым словам
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title",
                            "authors",
                            "journal",
                            "keywords.russian",
                            "annotation"
                        ],
                        "operator": "and"
                    }
                }
            }

        # Параметры пагинации
        from_ = (page - 1) * size

        # Выполняем запрос к Elasticsearch
        response = es.search(index="article", body=search_query, from_=from_, size=size)

        # Форматируем результат
        results = [
            {
                "id": hit["_id"],
                "title": hit["_source"]["title"],
                "authors": hit["_source"].get("authors", ""),
                "journal": hit["_source"].get("journal", ""),
                "year": hit["_source"].get("year", ""),
                "field_of_science": hit["_source"].get("field_of_science", ""),
                "keywords": hit["_source"].get("keywords", {}),
                "annotation": hit["_source"].get("annotation", ""),
                "citations": hit["_source"].get("citations", {}),
                "link": hit["_source"].get("link", "")
            }
            for hit in response["hits"]["hits"]
        ]

        return {
            #"page": page,
            #"size": size,
            #"total": response["hits"]["total"]["value"],
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")
