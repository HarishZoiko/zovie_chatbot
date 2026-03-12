FROM python:3.11-slim

WORKDIR /app

COPY backend_django/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend_django .

RUN python manage.py collectstatic --noinput

EXPOSE 8787

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8787"]