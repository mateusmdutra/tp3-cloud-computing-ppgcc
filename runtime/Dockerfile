FROM python:3.8-slim-buster

RUN chmod +x /app/entrypoint.sh
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

ENTRYPOINT ["/app/entrypoint.sh"]