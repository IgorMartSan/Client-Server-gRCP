FROM python:3.12

WORKDIR /code

RUN pip install --upgrade pip
# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Se o main.py fica em /app/app, ajuste o WORKDIR:
WORKDIR /code/src

CMD ["python", "main.py"]