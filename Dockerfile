# This is a simple Dockerfile to use while developing
# It's not suitable for production
#
# It allows you to run both flask and celery if you enabled it
# for flask: docker run --env-file=.flaskenv image flask run
# for celery: docker run --env-file=.flaskenv image celery worker -A myapi.celery_app:app
#
# note that celery will require a running broker and result backend
FROM python:3.7

ENV FLASK_APP=map.app:create_app

RUN mkdir /code
WORKDIR /code

# cache hack; very fragile
COPY requirements.txt ./
RUN pip install --requirement requirements.txt

COPY . /code/

RUN pip install -r requirements.txt

CMD gunicorn --bind "0.0.0.0:${PORT:-5000}" 'map.app:create_app()'

EXPOSE 5000
