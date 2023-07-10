FROM python:3.10.5

WORKDIR /app

ADD ./app /app

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade -r /app/requirements.txt

COPY . /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]