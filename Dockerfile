FROM python:3.10.5

WORKDIR /code

COPY requirements.txt /code/requirements.txt

RUN pip install --upgrade -r /code/requirements.txt

COPY . /code/

CMD ["uvicorn", "papercups_api:app", "--host", "0.0.0.0", "--port", "8000"]