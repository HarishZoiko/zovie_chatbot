FROM python:3.11-slim

WORKDIR /app

# copy requirements
COPY backend_django/requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY backend_django .

# collect static files
RUN python manage.py collectstatic --noinput

# run server
CMD exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT