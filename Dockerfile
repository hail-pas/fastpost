FROM python:3.8
RUN mkdir -p /usr/share/nginx/fastpost
RUN mkdir ~/.pip
RUN echo "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\nformat = columns" > ~/.pip/pip.conf
WORKDIR /usr/share/nginx/fastpost
COPY poetry.lock pyproject.toml /usr/share/nginx/fastpost/
RUN pip3 install poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
COPY . /usr/share/nginx/fastpost
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]