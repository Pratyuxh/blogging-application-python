FROM python:3.8
RUN pip install flask
RUN pip install flask_swagger_ui

WORKDIR /app

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py

CMD ["python", "main.py"]
