# rmq-rpc

Here is an example usage of rmq-rpc.

## Installation

You have to install docker first before running this. Make sure you have `docker compose` installed as well.

> See here for detailed information about docker: https://docs.docker.com/get-docker/

Then, clone this repo.

```
git clone https://github.com/aprilahijriyan/rmq-rpc.git
cd rmq-rpc
```

Make sure you have installed [python-pdm](https://pdm.fming.dev/latest/).

Then install all rmq-rpc dependencies.

```
pdm install -d
```

When it's done, go into the rmq-rpc environment.

```
source .venv/bin/activate
```

Go to the `examples/` directory

```
cd examples
```

Run RabbitMQ using `docker compose`

```
docker compose up -d --build
```

Run the RPC server

```
python server.py
```

Run the RPC client on a different terminal

```
python client.py
```
