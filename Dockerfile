FROM ijcai2022nmmo/submission-runtime:latest

WORKDIR /tmp/install

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# make sure keeping /home/aicrowd as WORKDIR !!!
WORKDIR /home/aicrowd
