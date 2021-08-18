import asyncio
from concurrent import futures

import grpc

from rpcs.hello import hello_pb2_grpc
from rpcs.hello.hello_pb2 import HelloOut, MultiHelloOut


class HelloServicer(hello_pb2_grpc.HelloServicer):

    async def HelloRPC(self, request, context):
        print(f"Simple RPC received request  ")
        res = HelloOut()
        res.infos = "Simple Nice to meet you!"
        return res

    async def MultiHelloRPC(self, request, context):
        print(f"Multi RPC received request  ")
        res = MultiHelloOut()
        for i in range(10):
            info = HelloOut()
            info.infos = f"Multi Nice to meet you! {i + 1}"
            res.replies.append(info)
        return res

    async def ResStreamHelloRPC(self, request, context):
        print(f"ResStream RPC received request  ")
        for i in range(10):
            info = HelloOut()
            info.infos = f"ResStream Nice to meet you! {i + 1}"
            yield info

    async def ReqStreamHelloRPC(self, request_iterator, context):
        print(f"ReqStream RPC received request ")
        res = MultiHelloOut()
        async for data in request_iterator:
            info = HelloOut()
            info.infos = f"ReqStream Nice to meet you! {data.name}"
            res.replies.append(info)

        return res

    async def BiStreamHelloRPC(self, request_iterator, context):
        print(f"BiStream RPC received request ")
        prev_names = []
        async for data in request_iterator:
            if data.name in prev_names:
                yield HelloOut(infos=f"Existed {data.name}")
            else:
                yield HelloOut(infos=f"New {data.name}")
                prev_names.append(data.name)


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    server.add_insecure_port('[::]:50055')
    hello_pb2_grpc.add_HelloServicer_to_server(HelloServicer(), server)
    await server.start()
    print("Starting...")
    await server.wait_for_termination()
    print("Terminated")


if __name__ == "__main__":
    asyncio.run(serve())
