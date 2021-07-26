FROM python:3.8
RUN mkdir -p /usr/share/nginx/fastpost
RUN mkdir ~/.pip
RUN echo "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\nformat = columns" > ~/.pip/pip.conf
ADD ./ /usr/share/nginx/fastpost
WORKDIR /usr/share/nginx/fastpost
RUN pip3 install poetry
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install
CMD ["gunicorn", "--config", "./deploy/gunicorn/conf.py", "--log-config", "./deploy/gunicorn/logging.conf", "main:app"]