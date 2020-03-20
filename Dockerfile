# This is a simple Dockerfile to use while developing
# It's not suitable for production
#
# It allows you to run both flask and celery if you enabled it
# for flask: docker run --env-file=.flaskenv image flask run
# for celery: docker run --env-file=.flaskenv image celery worker -A myapi.celery_app:app
#
# note that celery will require a running broker and result backend
FROM python:3.7

ENV FLASK_APP=map.app:create_app \
    FLASK_ENV=development

RUN mkdir /code
WORKDIR /code

COPY . /code/

RUN pip install -r requirements.txt

CMD flask run --host 0.0.0.0

EXPOSE 5000
