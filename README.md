# Zoikon Chatbot

AI-powered chatbot backend built with **Django** and **PostgreSQL**, featuring an automated **CI/CD pipeline using GitHub Actions**.

## Tech Stack

* Python
* Django
* PostgreSQL
* REST API
* GitHub Actions (CI/CD)

## Project Structure

backend_django/
├── chatbot/
├── config/
├── templates/
├── static/
├── manage.py
└── requirements.txt

## CI/CD Pipeline

The project includes an automated CI pipeline that runs on every push.

Pipeline steps:

1. Install Python dependencies
2. Start PostgreSQL service
3. Run Django system checks
4. Run database migrations
5. Execute tests

Workflow file:

.github/workflows/ci.yml

## Run Locally

Clone repository:

git clone https://github.com/harishreddy19/zovie-chatbot.git

Install dependencies:

pip install -r backend_django/requirements.txt

Run migrations:

python manage.py migrate

Start server:

python manage.py runserver

## Repository

GitHub Repository:

https://github.com/harishreddy19/zovie-chatbot
