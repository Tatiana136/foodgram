FROM python:3.9
WORKDIR /app
RUN pip install gunicorn
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi"]
