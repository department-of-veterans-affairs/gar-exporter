FROM python:3.6-alpine

ADD requirements.txt /usr/src/app/requirements.txt
RUN apk update
RUN apk --no-cache add openssl-dev gcc libffi-dev linux-headers musl-dev
RUN pip install -r /usr/src/app/requirements.txt

ENV CONFIG ./default.config.yml

ADD . /usr/src/app
WORKDIR /usr/src/app

CMD ["python", "gar_exporter.py"]
