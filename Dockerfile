FROM python:3.14-slim

WORKDIR /app

# instalar poetry
RUN pip install poetry

# copiar dependencias
COPY pyproject.toml poetry.lock /app/

# instalar dependencias
RUN poetry config virtualenvs.create false \
    && poetry install --no-root

# copiar código
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
