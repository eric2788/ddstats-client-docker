FROM python:3.8

WORKDIR /app

ENV BILIGO_HOST="blive.ericlamm.xyz"
ENV USE_TLS=true

COPY requirements.txt .
COPY *.py .

RUN pip3 install -r requirements.txt

CMD ["python3", "main.py"]
