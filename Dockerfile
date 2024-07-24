FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN mkdir /interface
WORKDIR /interface
RUN pip install --upgrade pip
COPY requirements.txt /interface/

RUN pip install -r requirements.txt
COPY interface /interface/

EXPOSE 20000

CMD ["gunicorn", "--bind", ":20000", "--workers", "3", "h4kslanding.wsgi:application"]
