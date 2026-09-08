FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/seis
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# `--no-proxy-headers` explícito: uvicorn trae `proxy_headers=True` por defecto y
# reescribiría `scope["client"]` por su cuenta con una semántica que ha cambiado
# entre versiones. Eso destruiría el par TCP, que es justamente el dato con el
# que `app/core/red.py` decide si puede fiarse de una cabecera. Dos capas
# resolviendo lo mismo con dos listas distintas es el peor de los mundos.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
