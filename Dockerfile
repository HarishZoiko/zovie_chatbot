FROM python:3.11-slim

WORKDIR /app

# copy requirements
COPY backend_django/requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy django project
COPY backend_django .

# collect static files
RUN python manage.py collectstatic --noinput

# start django with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 config.wsgi:application