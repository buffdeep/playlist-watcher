FROM python:3.9-alpine

COPY .cache playlist-watcher.py /playlist-watcher/
COPY requirements.txt /playlist-watcher

ADD auth/ /playlist-watcher/auth/

WORKDIR /playlist-watcher
RUN pip install -r requirements.txt
ENTRYPOINT [ "python" ]
CMD [ "playlist-watcher.py" ]
