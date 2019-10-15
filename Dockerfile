FROM python:3.6-alpine
EXPOSE 8000
ENV FC_SVC_NAME default
ENV FC_SVC_SECRET default_secret
ENV FC_SVC_HOST "0.0.0.0"
ENV FC_SVC_PORT 8000

RUN apk update && apk add curl

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt
CMD ["sh", "-c", "gunicorn -b ${FC_SVC_HOST}:${FC_SVC_PORT} -w 4 chain:app"]
