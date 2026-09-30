FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt requirements-ml.txt ./
ARG INSTALL_ML_DEPS=0
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt \
    && if [ "$INSTALL_ML_DEPS" = "1" ]; then \
         python -m pip install -r requirements-ml.txt; \
       fi

COPY . .

EXPOSE 8200

CMD ["python", "run.py"]
