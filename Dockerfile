FROM ijcai2022nmmo/submission-runtime:latest

WORKDIR /tmp/install

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# DO NOT MODIFY
WORKDIR /home/aicrowd
COPY my-submission my-submission
