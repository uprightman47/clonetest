FROM ijcai2022nmmo/submission-runtime:latest

WORKDIR /home/nmmo/install

COPY --chown=nmmo:nmmo requirements.txt requirements.txt

RUN pip install --user --no-cache-dir -r requirements.txt

# DO NOT MODIFY
WORKDIR /home/aicrowd
COPY --chown=nmmo:nmmo my-submission my-submission

