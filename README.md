
# is-wire

[![PyPI](https://img.shields.io/pypi/v/is-wire.svg?style=for-the-badge)](https://pypi.org/project/is-wire/)
[![Build](https://img.shields.io/github/actions/workflow/status/labvisio/is-wire-py/main.yml?style=for-the-badge)](https://github.com/labvisio/is-wire-py/actions)
[![Python suport](https://img.shields.io/pypi/pyversions/is-wire?style=for-the-badge)](https://pypi.org/project/is-wire)
[![Downloads](https://img.shields.io/pypi/dm/is-wire?style=for-the-badge)](https://pypi.org/project/is-wire/)

Pub/Sub middleware for the *is* architecture (python implementation)

## Installation 

Install the wire package using `pip` or `pipenv`:

```shell
  pip install --user is-wire
  # or
  pipenv install --user is-wire
```

## Usage

### Prepare environment

In order to send/receive messages an amqp broker is necessary, to create one simply run:

```shell
docker run -d --rm -p 5672:5672 -p 15672:15672 rabbitmq:3.7.6-management
```

### Basic send/receive

Create a channel to connect to a broker, create a subscription and subscribe to desired topics to receive messages:

```python
from is_wire.core import Channel, Subscription

# Connect to the broker
channel = Channel("amqp://guest:guest@localhost:5672")

# Subscribe to the desired topic(s)
subscription = Subscription(channel)
subscription.subscribe(topic="MyTopic.SubTopic")
# ... subscription.subscribe(topic="Other.Topic")

# Blocks forever waiting for one message from any subscription
message = channel.consume()
print(message)
```

Create and publish messages:

```python
from is_wire.core import Channel, Message

# Connect to the broker
channel = Channel("amqp://guest:guest@localhost:5672")

message = Message()
# Body is a binary field therefore we need to encode the string
message.body = "Hello!".encode('latin1')

# Broadcast message to anyone interested (subscribed)
channel.publish(message, topic="MyTopic.SubTopic")
```

Serialize/Deserialize protobuf objects:

```python
from is_wire.core import Channel, Message, Subscription, ContentType
from google.protobuf.struct_pb2 import Struct

channel = Channel("amqp://guest:guest@localhost:5672")

subscription = Subscription(channel)
subscription.subscribe(topic="MyTopic.SubTopic")

struct = Struct()
struct.fields["apples"].string_value = "red"

message = Message()
message.content_type = ContentType.JSON # or ContentType.PROTOBUF
message.pack(struct) # Serialize the struct into the message body

channel.publish(message, topic="MyTopic.SubTopic")

# Blocks forever waiting for the message we just sent
received_message = channel.consume()
# Deserialize the struct from the message body
received_struct = received_message.unpack(Struct) 

# Check that they are equal
assert struct == received_struct
```

### Basic Request/Reply 

Create a RPC Server:

```python
from is_wire.core import Channel, StatusCode, Status
from is_wire.rpc import ServiceProvider, LogInterceptor
from google.protobuf.struct_pb2 import Struct
import time


def increment(struct, ctx):
    if struct.fields["value"].number_value < 0:
        # Return error to client
        return Status(StatusCode.INVALID_ARGUMENT, "Number must be positive")

    time.sleep(0.2)  # Simulate work
    struct.fields["value"].number_value += 1.0
    # Return normal reply
    return struct


channel = Channel("amqp://guest:guest@localhost:5672")

provider = ServiceProvider(channel)
logging = LogInterceptor()  # Log requests to console
provider.add_interceptor(logging)

provider.delegate(
    topic="MyService.Increment",
    function=increment,
    request_type=Struct,
    reply_type=Struct)

provider.run() # Blocks forever processing requests
```

Send a request to the RPC Server:

```python
from is_wire.core import Channel, Message, Subscription
from google.protobuf.struct_pb2 import Struct
import socket

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)

# Prepare request
struct = Struct()
struct.fields["value"].number_value = 1.0
request = Message(content=struct, reply_to=subscription)
# Make request
channel.publish(request, topic="MyService.Increment")

# Wait for reply with 1.0 seconds timeout
try:
    reply = channel.consume(timeout=1.0)
    struct = reply.unpack(Struct)
    print('RPC Status:', reply.status, '\nReply:', struct)
except socket.timeout:
    print('No reply :(')
```

Multiples requests can be done throughout same client. To distinguish which reply is related to each request, you can use the `correlation_id`. This attribute is always set when a `Message` is published containing `reply_to` parameter, which means that it was a RPC request. Example below shows how to deal with it.

```python
from is_wire.core import Channel, Message, Subscription
from google.protobuf.struct_pb2 import Struct
import socket

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)

# Prepare first request
struct = Struct()
struct.fields["value"].number_value = 1.0
request_1 = Message(content=struct, reply_to=subscription)

# Prepare second request
struct = Struct()
struct.fields["value"].number_value = 2.0
request_2 = Message(content=struct, reply_to=subscription)

# Make requests
channel.publish(request_1, topic="MyService.Increment")
channel.publish(request_2, topic="MyService.Increment")

# Wait for replies with 1.0 seconds timeout
n_replies = 0
while n_replies < 2:
    try:
        reply = channel.consume(timeout=1.0)
        struct = reply.unpack(Struct)
        if reply.correlation_id == request_1.correlation_id:
            n_replies += 1
            print('First Request\nRPC Status:', reply.status, '\nReply:', struct)
        elif reply.correlation_id == request_2.correlation_id:
            n_replies += 1
            print('Second Request\nRPC Status:', reply.status, '\nReply:', struct)
        else:
            print('Unexpected message')
    except socket.timeout:
        print('No reply :(')
```

### Tracing messages

This middleware uses [opencensus](https://github.com/census-instrumentation/opencensus-python) as instrumentation library. Latest versions of opencensus released separate packages to integrate with different frameworks and tracing collector tools. When interacting with services implemented with either the C++ or Python of is-wire, we recommend to use [Zipkin](https://zipkin.apache.org/) to collect the tracing data. To do so, use the latest version of [OpenCensus Zipkin Exporter](https://github.com/census-instrumentation/opencensus-python/tree/master/contrib/opencensus-ext-zipkin).

Instantiate an Exporter to trace requests:

```python
from is_wire.core import AsyncTransport
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter

# Create an exporter, change values accordingly to match your zipkin server
exporter = ZipkinExporter(
    service_name="MyService",
    host_name="localhost",
    port=9411,
    transport=AsyncTransport,
)
```

Then create a tracer and start tracing:

```python
from is_wire.core import Channel, Message, Tracer

channel = Channel("amqp://guest:guest@localhost:5672") 
tracer = Tracer(exporter)

with tracer.span(name="publish") as span:
    message = Message()
    # ...
    # Propagates the current tracing context
    message.inject_tracing(span) 
    channel.publish(message, topic="Any.Topic")
```
Or create a tracing interceptor and pass it to your ServiceProvider:

```python
from is_wire.rpc import TracingInterceptor, ServiceProvider

channel = Channel("amqp://guest:guest@localhost:5672") 

provider = ServiceProvider(channel)

tracing = TracingInterceptor(exporter)  # automatically trace requests
provider.add_interceptor(tracing)
```

## Development

### Tests

```shell
# prepare environment
pip install --user tox
docker run -d --rm -p 5672:5672 -p 15672:15672 rabbitmq:3.7.6-management

# run all the tests
tox
```
