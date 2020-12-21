import json
import os
import sys

sys.path.append(os.getcwd())
import time
from _ctypes import Structure
from ctypes import c_byte, c_uint16, c_uint32
from instrument.RPC import pre_call, get_usb_rpc
from util import logging

log = logging.getLogger(__name__)


def networking(rpc, file_path: str = None):
    headers = {
        0: ['InterfaceIndex', "Name"],
        1: ['LocalAddress', 'RemoteAddress', 'InterfaceIndex', 'Pid', 'RecvBufferSize', 'RecvBufferUsed',
            'SerialNumber', 'Kind'],
        2: ['RxPackets', 'RxBytes', 'TxPackets', 'TxBytes', 'RxDups', 'RxOOO', 'TxRetx', 'MinRTT', 'AvgRTT',
            'ConnectionSerial']
    }
    msg_type = {
        0: "interface-detection",
        1: "connection-detected",
        2: "connection-update",
    }

    def on_callback_message(res):
        from socket import inet_ntoa, htons, inet_ntop, AF_INET6
        class SockAddr4(Structure):
            _fields_ = [
                ('len', c_byte),
                ('family', c_byte),
                ('port', c_uint16),
                ('addr', c_byte * 4),
                ('zero', c_byte * 8)
            ]

            def __str__(self):
                return f"{inet_ntoa(self.addr)}:{htons(self.port)}"

        class SockAddr6(Structure):
            _fields_ = [
                ('len', c_byte),
                ('family', c_byte),
                ('port', c_uint16),
                ('flowinfo', c_uint32),
                ('addr', c_byte * 16),
                ('scopeid', c_uint32)
            ]

            def __str__(self):
                return f"[{inet_ntop(AF_INET6, self.addr)}]:{htons(self.port)}"

        data = res.parsed
        if data[0] == 1:
            if len(data[1][0]) == 16:
                data[1][0] = str(SockAddr4.from_buffer_copy(data[1][0]))
                data[1][1] = str(SockAddr4.from_buffer_copy(data[1][1]))
            elif len(data[1][0]) == 28:
                data[1][0] = str(SockAddr6.from_buffer_copy(data[1][0]))
                data[1][1] = str(SockAddr6.from_buffer_copy(data[1][1]))
        if file_path:
            temp_dict = dict(zip(headers[data[0]], data[1]))
            temp_dict["msg_type"] = msg_type[data[0]]
            with open(file_path, 'a+') as file:
                file.write(json.dumps(temp_dict) + os.linesep)
        log.debug(msg_type[data[0]] + json.dumps(dict(zip(headers[data[0]], data[1]))))
        # print("[data]", res.parsed)

    pre_call(rpc)
    rpc.register_channel_callback("com.apple.instruments.server.services.networking", on_callback_message)
    var = rpc.call("com.apple.instruments.server.services.networking", "replayLastRecordedSession").parsed
    log.debug("replay" + str(var))
    var = rpc.call("com.apple.instruments.server.services.networking", "startMonitoring").parsed
    log.debug("start", str(var))
    time.sleep(10)
    var = rpc.call("com.apple.instruments.server.services.networking", "stopMonitoring").parsed
    log.debug("stopMonitoring", str(var))
    rpc.stop()


if __name__ == '__main__':
    rpc = get_usb_rpc()
    networking(rpc, "test2.txt")
    rpc.deinit()