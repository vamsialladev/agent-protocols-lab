FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt requirements-nodeps.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && pip install --no-cache-dir --no-deps -r requirements-nodeps.txt
COPY . .
ENV PYTHONPATH=src
RUN useradd --create-home lab && chown -R lab /app
USER lab
CMD ["python", "-m", "pytest"]
