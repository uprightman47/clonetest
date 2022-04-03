FROM python:3.9.11

WORKDIR /tmp/install

# set the pip index-url you need
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

COPY requirements_base.txt requirements_base.txt

RUN pip install --no-cache-dir -r requirements_base.txt

COPY requirements_nmmo.txt requirements_nmmo.txt

RUN pip install --no-cache-dir -r requirements_nmmo.txt

RUN useradd -m nmmo

USER nmmo

WORKDIR /home/nmmo

CMD ["bash"]

