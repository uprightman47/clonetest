FROM python:3.9.11

RUN useradd -u 1001 -d /home/nmmo --create-home nmmo

USER nmmo

WORKDIR /home/nmmo/install

# set the pip index-url you need
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

COPY --chown=nmmo:nmmo requirements_base.txt requirements_base.txt

RUN pip install --user --no-cache-dir -r requirements_base.txt

COPY --chown=nmmo:nmmo requirements_nmmo.txt requirements_nmmo.txt

RUN pip install --user --no-cache-dir -r requirements_nmmo.txt

ENV PATH "${PATH}:/home/nmmo/.local/bin/"
ENV PYTHONPATH "${PYTHONPATH}:/home/nmmo/.local/lib/python3.9/site-packages/"

