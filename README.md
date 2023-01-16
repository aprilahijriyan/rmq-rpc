# rmq-rpc

A lightweight RPC based on RabbitMQ.

## Installation

Install the module using `pip`:

```
pip install rmq-rpc
```

## Features

- [x] Multiple serializer types support

    - [x] Pickle (Enabled by default)
    - [x] JSON
    - [ ] MsgPack

- [x] Task error handling
- [x] Task cancellation

## Examples

See [project examples](https://github.com/aprilahijriyan/rmq-rpc/tree/main/examples)

## FAQ

- Can I use the same 'exchange' for server and client ?

> Certainly not. Because an 'exchange' is required to send a message to a specific queue associated with that exchange.

- What exchange types are supported?

> I've tested it using the `direct` and `topic` exchange types it seems to work fine. Besides, it may not work.
