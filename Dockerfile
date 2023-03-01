FROM python:3.8

WORKDIR /app

ENV BILIGO_WS_URL="blive.ericlamm.xyz"
ENV USE_TLS=true

COPY requirements.txt .
COPY *.py .

RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3" ]
CMD ["main.py"]
