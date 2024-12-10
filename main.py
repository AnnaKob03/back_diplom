# from fastapi import FastAPI, HTTPException, Query
# from fastapi.responses import FileResponse
# from elasticsearch import Elasticsearch
# from dotenv import load_dotenv
# import os
#
# # Загрузка переменных окружения
# load_dotenv()
#
# # URL Elasticsearch из файла окружения
# ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
#
# if not ELASTICSEARCH_URL:
#     raise Exception("ELASTICSEARCH_URL is not defined in the environment variables.")
#
# # Создание приложения
# app = FastAPI()
#
# # Подключение к Elasticsearch
# try:
#     es = Elasticsearch(ELASTICSEARCH_URL)
# except Exception as e:
#     raise Exception(f"Error connecting to Elasticsearch: {e}")
#
# # Проверка доступности Elasticsearch при старте приложения
# @app.on_event("startup")
# def check_elasticsearch():
#     try:
#         if not es.ping():
#             raise HTTPException(status_code=500, detail="Elasticsearch is not reachable.")
#     except Exception as e:
#         raise Exception(f"Failed to check Elasticsearch health: {e}")
#
# # Эндпоинт для проверки состояния Elasticsearch
# @app.get("/health")
# def health_check():
#     if es.ping():
#         return {"status": "Elasticsearch is reachable"}
#     raise HTTPException(status_code=500, detail="Elasticsearch is not reachable")
#
# # Главная страница
# @app.get("/")
# def read_root():
#     return {"message": "Welcome to FastAPI application!"}
#
# # Favicon (необязательно)
# @app.get("/favicon.ico", include_in_schema=False)
# def favicon():
#     return FileResponse("favicon.ico")
#
# # Эндпоинт для поиска статей
# @app.get("/search")
# def search_articles(
#     query: str = Query(None, description="Search query"),
#     page: int = Query(1, ge=1, description="Page number (starting from 1)"),
#     size: int = Query(100, ge=1, le=1000, description="Number of results per page (max 1000)")
# ):
#     try:
#         # Формируем запрос к Elasticsearch
#         search_query = {
#             "query": {
#                 "match_all": {}
#             }
#         } if not query else {
#             "query": {
#                 "multi_match": {
#                     "query": query,
#                     "fields": [
#                         "title",
#                         "authors",
#                         "journal",
#                         "keywords.russian",
#                         "annotation"
#                     ],
#                     "operator": "and"
#                 }
#             }
#         }
#
#         # Параметры пагинации
#         from_ = (page - 1) * size
#
#         # Выполнение запроса
#         response = es.search(index="article", body=search_query, from_=from_, size=size)
#
#         # Форматирование результатов
#         results = [
#             {
#                 "id": hit["_id"],
#                 "title": hit["_source"].get("title", ""),
#                 "authors": hit["_source"].get("authors", ""),
#                 "journal": hit["_source"].get("journal", ""),
#                 "year": hit["_source"].get("year", ""),
#                 "field_of_science": hit["_source"].get("field_of_science", ""),
#                 "keywords": hit["_source"].get("keywords", {}),
#                 "annotation": hit["_source"].get("annotation", ""),
#                 "citations": hit["_source"].get("citations", {}),
#                 "link": hit["_source"].get("link", "")
#             }
#             for hit in response["hits"]["hits"]
#         ]
#
#         return results
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Получение переменных из .env
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS").split(",")
CACHE_CONTROL = os.getenv("CACHE_CONTROL")
APP_PORT = int(os.getenv("APP_PORT"))
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Проверка обязательных переменных
if not ELASTICSEARCH_URL or not ELASTICSEARCH_INDEX:
    raise Exception("ELASTICSEARCH_URL or ELASTICSEARCH_INDEX is not defined in the environment variables.")

# Создание приложения
app = FastAPI()

# Добавление CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Elasticsearch
try:
    es = Elasticsearch(ELASTICSEARCH_URL)
except Exception as e:
    raise Exception(f"Error connecting to Elasticsearch: {e}")

# Проверка доступности Elasticsearch при старте приложения
@app.on_event("startup")
def check_elasticsearch():
    try:
        if not es.ping():
            raise HTTPException(status_code=500, detail="Elasticsearch is not reachable.")
    except Exception as e:
        raise Exception(f"Failed to check Elasticsearch health: {e}")

# Эндпоинт для проверки состояния Elasticsearch
@app.get("/health")
def health_check():
    if es.ping():
        return {"status": "Elasticsearch is reachable"}
    raise HTTPException(status_code=500, detail="Elasticsearch is not reachable")

# Главная страница
@app.get("/")
def read_root():
    return {"message": "Welcome to FastAPI application!", "environment": ENVIRONMENT}


# Эндпоинт для поиска статей
@app.get("/search")
def search_articles(
    query: str = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    size: int = Query(100, ge=1, le=1000, description="Number of results per page (max 1000)")
):
    try:
        # Формируем запрос к Elasticsearch
        search_query = {
            "query": {
                "match_all": {}
            }
        } if not query else {
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

        # Выполнение запроса
        response = es.search(index=ELASTICSEARCH_INDEX, body=search_query, from_=from_, size=size)

        # Форматирование результатов
        results = [
            {
                "id": hit["_id"],
                "title": hit["_source"].get("title", ""),
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

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")

# Указываем FastAPI отдавать файлы из папки "visualizations"
app.mount("/visualizations", StaticFiles(directory="visualizations"), name="visualizations")

# Эндпоинт для отдачи файлов визуализаций
@app.get("/visualizations/{filename}")
async def get_visualization(filename: str):
    return FileResponse(f"visualizations/{filename}", headers={
        "Cache-Control": CACHE_CONTROL
    })
