from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
from fastapi.responses import HTMLResponse

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


# Указываем FastAPI отдавать файлы из папки "visualizations"
app.mount("/visualizations", StaticFiles(directory="visualizations"), name="visualizations")


# Эндпоинт для отдачи файлов визуализаций
@app.get("/visualizations/{filename}")
async def get_visualization(filename: str):
    return FileResponse(f"visualizations/{filename}", headers={
        "Cache-Control": CACHE_CONTROL
    })


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



# год
@app.get("/generate_histogram_year", response_class=HTMLResponse)
def generate_histogram(
        topic_number: int = Query(..., description="Topic number to filter articles by")
):
    try:
        # Формируем запрос для поиска статей
        query = {
            "query": {
                "term": {"topic_number": topic_number}
            },
            "size": 1000  # Ограничиваем размер результата
        }

        response = es.search(index=ELASTICSEARCH_INDEX, body=query)

        # Собираем данные
        articles = response["hits"]["hits"]
        if not articles:
            raise HTTPException(status_code=404, detail="No data found for the given topic_number.")

        year_counts = {}
        for article in articles:
            year = article["_source"].get("year", "Unknown")
            year_counts[year] = year_counts.get(year, 0) + 1

        # Данные для построения графика
        years = sorted(year_counts.keys())  # Сортируем года по возрастанию
        counts = [year_counts[year] for year in years]

        if not years or not counts:
            raise HTTPException(status_code=404, detail="No data found for the given topic_number.")

        # Построение графика с использованием Plotly
        fig = go.Figure(data=[
            go.Bar(x=years, y=counts, marker_color='rgb(117, 185, 117)')
        ])

        fig.update_layout(
            xaxis_title="Год",
            yaxis_title="Количество статей",
            xaxis=dict(
                tickmode='linear',  # Обеспечивает отображение всех категорий на оси X
                tickangle=45,  # Угол поворота подписей
                tickfont=dict(color='black')  # Цвет подписей на оси X
            ),
            yaxis=dict(
                tickfont=dict(color='black')  # Цвет подписей на оси Y
            ),
            title_font=dict(
                color='black',  # Цвет заголовка
                size=16  # Размер заголовка
            ),
            xaxis_title_font=dict(
                color='black'  # Цвет заголовка оси X
            ),
            yaxis_title_font=dict(
                color='black'  # Цвет заголовка оси Y
            ),
            height=600,
            width=1000,
            plot_bgcolor='rgb(229, 254, 229)',  # Цвет фона
            font=dict(color='black')  # Общий цвет текста
        )

        # Генерация HTML
        html_content = fig.to_html(full_html=False)

        # Встраиваем график в HTML-страницу
        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        return HTMLResponse(content=html_page)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")


# раздел
@app.get("/generate_pie_chart", response_class=HTMLResponse)
def generate_pie_chart(
        topic_number: int = Query(..., description="Topic number to filter articles by")
):
    try:
        # Формируем запрос для поиска статей
        query = {
            "query": {
                "term": {"topic_number": topic_number}
            },
            "size": 1000  # Ограничиваем размер результата
        }

        response = es.search(index=ELASTICSEARCH_INDEX, body=query)

        # Собираем данные
        articles = response["hits"]["hits"]
        if not articles:
            raise HTTPException(status_code=404, detail="No data found for the given topic_number.")

        field_counts = {}
        for article in articles:
            field = article["_source"].get("field_of_science", "Unknown")
            field_counts[field] = field_counts.get(field, 0) + 1

        # Данные для построения графика
        fields = list(field_counts.keys())
        counts = [field_counts[field] for field in fields]

        if not fields or not counts:
            raise HTTPException(status_code=404, detail="No data found for the given topic_number.")

        # Построение круговой диаграммы с использованием Plotly
        colors = ['rgb(184, 219, 184)', 'rgb(139, 196, 139)', 'rgb(95, 174, 95)', 'rgb(68, 134, 68)', 'rgb(45, 89, 45)', 'rgb(23, 45, 23)']
        fig = go.Figure(data=[
            go.Pie(
                labels=fields,
                values=counts,
                hoverinfo='percent+label',  # Проценты отображаются при наведении
                marker=dict(colors=colors)
            )
        ])

        fig.update_layout(
            title=dict(
                font=dict(color='black', size=16)
            ),
            legend=dict(
                orientation="v",  # Вертикальное расположение легенды
                x=1.2,  # Смещение легенды вправо
                y=0.5,
                traceorder="normal",
                font=dict(
                    size=12,
                    color="black"
                )
            ),
            margin=dict(l=50, r=50, t=50, b=50),  # Уменьшаем отступы для компактности
            height=600,
            width=1000,
        )

        # Генерация HTML
        html_content = fig.to_html(full_html=False)

        # Встраиваем график в HTML-страницу
        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        return HTMLResponse(content=html_page)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")

