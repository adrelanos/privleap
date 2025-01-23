#!/usr/bin/python3 -u

# Copyright (C) 2025 - 2025 ENCRYPTED SUPPORT LLC <adrelanos@whonix.org>
# See the file COPYING for copying conditions.

# privleap.py - Backend library for privleap clients and servers.

from enum import Enum
import socket
import os
import stat
import pwd
from io import StringIO
import re

class PrivleapSocketType(Enum):
    CONTROL = 1
    COMMUNICATION = 2

class PrivleapValidateType(Enum):
    USER_GROUP_NAME = 1
    CONFIG_FILE = 2
    SIGNAL_NAME = 3

class PrivleapControlClientCreateMsg:
    user_name = None

    def __init__(self, user_name: str):
        if not PrivleapCommon.validate_id(user_name, PrivleapValidateType.USER_GROUP_NAME):
            raise ValueError("Specified username is invalid.")
        self.user_name = user_name

    def serialize(self):
        return "CREATE {0}".format(self.user_name).encode("utf-8")

class PrivleapControlClientDestroyMsg:
    user_name = None

    def __init__(self, user_name: str):
        if not PrivleapCommon.validate_id(user_name, PrivleapValidateType.USER_GROUP_NAME):
            raise ValueError("Specified username is invalid.")
        self.user_name = user_name

    def serialize(self):
        return "DESTROY {0}".format(self.user_name).encode("utf-8")

class PrivleapControlServerOkMsg:
    @staticmethod
    def serialize():
        return "OK".encode("utf-8")

class PrivleapControlServerControlErrorMsg:
    @staticmethod
    def serialize():
        return "CONTROL_ERROR".encode("utf-8")

class PrivleapControlServerExistsMsg:
    @staticmethod
    def serialize():
        return "EXISTS".encode("utf-8")

class PrivleapControlServerNouserMsg:
    @staticmethod
    def serialize():
        return "NOUSER".encode("utf-8")

class PrivleapCommClientSignalMsg:
    signal_name = None

    def __init__(self, signal_name: str):
        if not PrivleapCommon.validate_id(signal_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified signal name is invalid.")
        self.signal_name = signal_name

    def serialize(self):
        return "SIGNAL {0}".format(self.signal_name).encode("utf-8")

class PrivleapCommServerTriggerMsg:
    action_name = None

    def __init__(self, action_name: str):
        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified action name is invalid.")
        self.action_name = action_name

    def serialize(self):
        return "TRIGGER {0}".format(self.action_name).encode("utf-8")

class PrivleapCommServerTriggerErrorMsg:
    action_name = None

    def __init__(self, action_name: str):
        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified action name is invalid.")
        self.action_name = action_name

    def serialize(self):
        return "TRIGGER_ERROR {0}".format(self.action_name).encode("utf-8")

class PrivleapCommServerResultStdoutMsg:
    action_name = None
    stdout_bytes = None

    def __init__(self, action_name: str, stdout_bytes: bytes):
        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified action name is invalid.")
        self.action_name = action_name
        self.stdout_bytes = stdout_bytes

    def serialize(self):
        return "RESULT_STDOUT {0} ".format(self.action_name).encode("utf-8") + self.stdout_bytes

class PrivleapCommServerResultStderrMsg:
    action_name = None
    stderr_bytes = None

    def __init__(self, action_name: str, stderr_bytes: bytes):
        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified action name is invalid.")
        self.action_name = action_name
        self.stderr_bytes = stderr_bytes

    def serialize(self):
        return "RESULT_STDERR {0} ".format(self.action_name).encode("utf-8") + self.stderr_bytes

class PrivleapCommServerResultExitcodeMsg:
    action_name = None
    exit_code = None

    def __init__(self, action_name: str, exit_code: str):
        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Specified action name is invalid.")
        self.action_name = action_name
        self.exit_code = exit_code

    def serialize(self):
        return "RESULT_EXITCODE {0} {1}" . format(self.action_name, self.exit_code).encode("utf-8")

class PrivleapCommServerUnauthorizedMsg:
    @staticmethod
    def serialize():
        return "UNAUTHORIZED".encode("utf-8")

class PrivleapSocket:
    backend_socket = None
    socket_type = None
    user_name = None

    def __init__(self, socket_type: PrivleapSocketType, user_name: str = ""):
        if socket_type == PrivleapSocketType.CONTROL:
            if user_name != "":
                raise ValueError("user_name is only valid with PrivleapSocketType.COMMUNICATION")
            self.backend_socket = socket.socket(family = socket.AF_UNIX)
            self.backend_socket.bind(PrivleapCommon.control_path)
            os.chown(PrivleapCommon.control_path, 0, 0)
            os.chmod(PrivleapCommon.control_path, stat.S_IRUSR | stat.S_IWUSR)
            self.backend_socket.listen(10)
        else:
            if user_name == "":
                raise ValueError("user_name must be provided when using PrivleapSocketType.COMMUNICATION")

            if not PrivleapCommon.validate_id(user_name, PrivleapValidateType.USER_GROUP_NAME):
                raise ValueError("User name '" + user_name + "' is invalid.")

            try:
                user_info = pwd.getpwnam(user_name)
                target_uid = user_info.pw_uid
                target_gid = user_info.pw_gid
            except:
                raise ValueError("User '" + user_name + "' does not exist.")

            self.backend_socket = socket.socket(family = socket.AF_UNIX)
            socket_path = PrivleapCommon.comm_path + "/" + user_name
            self.backend_socket.bind(socket_path)
            os.chown(socket_path, target_uid, target_gid)
            os.chmod(socket_path, stat.S_IRUSR | stat.S_IWUSR)
            self.backend_socket.listen(10)
            self.user_name = user_name

        self.socket_type = socket_type

    def get_session(self):
        # socket.accept returns a (socket, address) tuple, we only need the
        # socket from this
        session_socket = self.backend_socket.accept()[0]
        if self.socket_type == PrivleapSocketType.CONTROL:
            return PrivleapSession(session_socket, is_control_session = True)
        else:
            return PrivleapSession(session_socket, user_name = self.user_name, is_control_session = False)

class PrivleapSession:
    backend_socket = None
    is_control_session = False
    is_server_side = False
    is_session_open = False
    user_name = None

    # Only an extremely poorly designed client or server will ever fail to work
    # quickly enough for a 0.1-second timeout to be too short. On the other hand
    # a malicious client may attempt to lock up privleapd by sending incomplete
    # data and then hanging forever, so we timeout very quickly to avoid this
    # attack.
    def __init__(self, session_info, user_name: str = "", is_control_session: bool = False):
        if type(session_info) is str:
            if user_name != "":
                raise ValueError("user_name cannot be passed if session_info is a string")

            if is_control_session:
                socket_path = PrivleapCommon.control_path

            else:
                if not PrivleapCommon.validate_id(session_info, PrivleapValidateType.USER_GROUP_NAME):
                    raise ValueError("User name'" + session_info + "'is invalid.")

                self.user_name = session_info
                socket_path = PrivleapCommon.comm_path + '/' + session_info

            if not os.access(socket_path, os.R_OK | os.W_OK):
                raise PermissionError("Cannot access '" + socket_path + "' for reading and writing")

            self.backend_socket = socket.socket(family=socket.AF_UNIX)
            self.backend_socket.connect(socket_path)
            self.backend_socket.settimeout(0.1)

        elif type(session_info) is socket.socket:
            if user_name != "" and not PrivleapCommon.validate_id(user_name, PrivleapValidateType.USER_GROUP_NAME):
                raise ValueError("User name '" + user_name + "' is invalid.")

            self.backend_socket = session_info
            self.user_name = user_name
            self.backend_socket.settimeout(0.1)
            self.is_server_side = True

        else:
            raise ValueError("session_info must be either type 'str' or type 'socket'")

        self.is_control_session = is_control_session
        self.is_session_open = True

    # DO NOT USE __recv_msg ON THE SERVER! This is intentionally vulnerable
    # to a denial-of-service attack where the remote process deliberately sends
    # data slowly (or just refuses to send data at all) in order to lock up the
    # local process. This is safe for the client (which may need to receive very
    # large amounts of data from the server), but dangerous for the server
    # (which needs to not lock up if a client tries to cause large delays).
    def __recv_msg(self):
        header_len = 4
        recv_buf = b''

        while len(recv_buf) != header_len:
            try:
                tmp_buf = self.backend_socket.recv(header_len - len(recv_buf))
            except socket.timeout:
                continue
            if tmp_buf == b'':
                raise ConnectionAbortedError("Connection unexpectedly closed")
            recv_buf += tmp_buf

        msg_len = int.from_bytes(recv_buf, byteorder='big')

        if self.is_server_side:
            if msg_len > 4096:
                raise ValueError("Received message is too long")

        recv_buf = b''

        while len(recv_buf) != msg_len:
            try:
                tmp_buf = self.backend_socket.recv(msg_len - len(recv_buf))
            except socket.timeout:
                continue
            if tmp_buf == b'':
                raise ConnectionAbortedError("Connection unexpectedly closed")
            recv_buf += tmp_buf

        return recv_buf

    # While there aren't security issues with doing so, you probably shouldn't
    # use __recv_msg_cautious on the client. It may result in a disconnect
    # while the server is still trying to send data to the client. It bails out
    # if a read times out, or if it takes more than five combined loop
    # iterations to read a message (thus giving at most ~0.5 seconds for the
    # client to send a whole message).
    def __recv_msg_cautious(self):
        max_loops = 5
        header_len = 4
        recv_buf = b''

        while len(recv_buf) != header_len:
            if max_loops == 0:
                raise ConnectionAbortedError("Connection is too slow")
            try:
                tmp_buf = self.backend_socket.recv(header_len - len(recv_buf))
            except socket.timeout:
                raise ConnectionAbortedError("Connection locked up")
            if tmp_buf == b'':
                raise ConnectionAbortedError("Connection unexpectedly closed")
            recv_buf += tmp_buf
            max_loops -= 1

        msg_len = int.from_bytes(recv_buf, byteorder='big')
        recv_buf = b''

        while len(recv_buf) != msg_len:
            if max_loops == 0:
                raise ConnectionAbortedError("Connection is too slow")
            try:
                tmp_buf = self.backend_socket.recv(msg_len - len(recv_buf))
            except socket.timeout:
                raise ConnectionAbortedError("Connection locked up")
            if tmp_buf == b'':
                raise ConnectionAbortedError("Connection unexpectedly closed")
            recv_buf += tmp_buf
            max_loops -= 1

        return recv_buf

    @staticmethod
    def __get_msg_type_field(recv_buf: bytes):
        # Default to the length of the recv_buf if no space is found
        type_field_len = len(recv_buf)

        # Find first ASCII space, if it exists
        for idx, byte_val in enumerate(recv_buf):
            # Don't allow anything other than printable 7-bit-ASCII in the type
            # field
            if byte_val < 0x1F or byte_val > 0x7F:
                raise ValueError("Invalid byte found in ASCII string data")
            if byte_val == 0x20:
                type_field_len = idx
                break

        return recv_buf[:type_field_len].decode("utf-8")

    @staticmethod
    def __parse_msg_parameters(recv_buf: bytes, str_count: int, blob_at_end: bool):
        output_list = list()
        recv_buf_pos = 0

        # __parse_msg_parameters has to ignore the first string in the
        # message, since the first string is the message type, not a parameter.
        # Thus we have to parse one more string than specified by str_count.
        for i in range(0, str_count + 1):
            if recv_buf_pos == len(recv_buf):
                raise ValueError("Unexpected end of recv_buf hit")

            space_idx = len(recv_buf)
            for j in range(recv_buf_pos, len(recv_buf)):
                # Don't allow anything other than printable 7-bit-ASCII in the type
                # field
                byte_val = recv_buf[j]
                if byte_val < 0x1F or byte_val > 0x7F:
                    raise ValueError("Invalid byte found in ASCII string data")
                if byte_val == 0x20:
                    space_idx = j
                    break

            # Ignore the message type field, we parsed that out already in
            # __get_msg_type_field
            if i == 0:
                # If space_idx isn't equal to len(recv_buf), we hit an actual space,
                # so we want to pick up scanning immediately *after* that space. If
                # space_idx is equal to len(recv_buf) though, it's already at an
                # index equal to one past the end of the data buffer, so there's no
                # need to increment it.
                if space_idx != len(recv_buf):
                    recv_buf_pos = space_idx + 1
                else:
                    recv_buf_pos = space_idx
                continue

            # Grab the detected string
            found_string = recv_buf[recv_buf_pos:space_idx].decode("utf-8")
            output_list.append(found_string)

            if space_idx != len(recv_buf):
                recv_buf_pos = space_idx + 1
            else:
                recv_buf_pos = space_idx

        # At this point output_list contains all of the strings we want. If
        # blob_at_end is false, we *must* be at the end of recv_buf, or
        # someone's trying to pass buggy or malicious data. If blob_at_end is
        # true, we want to take all remaining data in the recv_buf and return it
        # as the blob.
        if blob_at_end:
            if recv_buf_pos == len(recv_buf):
                blob = b''
            else:
                blob = recv_buf[recv_buf_pos:len(recv_buf)]
            output_list.append(blob)
        else:
            if recv_buf_pos != len(recv_buf):
                raise ValueError("recv_buf contains data past the last string")

        return output_list


    def get_msg(self):
        if not self.is_session_open:
            raise IOError("Session is closed.")

        if self.is_server_side:
            recv_buf = self.__recv_msg_cautious()
        else:
            recv_buf = self.__recv_msg()
        msg_type_str = self.__get_msg_type_field(recv_buf)

        # Note, we parse the arguments of every single message type, even if the
        # message should have no arguments. This is because the parser ensures
        # that the message is well-formed, and we do not want to accept a
        # technically usable but ill-formed message for security reasons.

        # Server-side control socket, we're receiving, so expect client control messages
        if self.is_control_session and self.is_server_side:
            if msg_type_str == "CREATE":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = False)
                return PrivleapControlClientCreateMsg(param_list[0])
            elif msg_type_str == "DESTROY":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = False)
                return PrivleapControlClientDestroyMsg(param_list[0])
            else:
                raise ValueError("Invalid message type '" + msg_type_str + "' for socket")
        # Client-side control socket, we're receiving, so expect server control messages
        elif self.is_control_session and not self.is_server_side:
            if msg_type_str == "OK":
                self.__parse_msg_parameters(recv_buf, str_count = 0, blob_at_end = False)
                return PrivleapControlServerOkMsg()
            elif msg_type_str == "CONTROL_ERROR":
                self.__parse_msg_parameters(recv_buf, str_count = 0, blob_at_end = False)
                return PrivleapControlServerControlErrorMsg()
            elif msg_type_str == "EXISTS":
                self.__parse_msg_parameters(recv_buf, str_count = 0, blob_at_end = False)
                return PrivleapControlServerExistsMsg()
            elif msg_type_str == "NOUSER":
                self.__parse_msg_parameters(recv_buf, str_count = 0, blob_at_end = False)
                return PrivleapControlServerNouserMsg()
            else:
                raise ValueError("Invalid message type '" + msg_type_str + "' for socket")
        # Server-side comm socket, we're receiving, so expect client comm messages
        elif not self.is_control_session and self.is_server_side:
            if msg_type_str == "SIGNAL":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = False)
                return PrivleapCommClientSignalMsg(param_list[0])
            else:
                raise ValueError("Invalid message type '" + msg_type_str + "' for socket")
        # Client-side comm socket, we're receiving, so expect server comm messages
        else:
            if msg_type_str == "TRIGGER":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = False)
                return PrivleapCommServerTriggerMsg(param_list[0])
            elif msg_type_str == "TRIGGER_ERROR":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = False)
                return PrivleapCommServerTriggerErrorMsg(param_list[0])
            elif msg_type_str == "RESULT_STDOUT":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = True)
                return PrivleapCommServerResultStdoutMsg(param_list[0], param_list[1])
            elif msg_type_str == "RESULT_STDERR":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 1, blob_at_end = True)
                return PrivleapCommServerResultStderrMsg(param_list[0], param_list[1])
            elif msg_type_str == "RESULT_EXITCODE":
                param_list = self.__parse_msg_parameters(recv_buf, str_count = 2, blob_at_end = False)
                return PrivleapCommServerResultExitcodeMsg(param_list[0], param_list[1])
            elif msg_type_str == "UNAUTHORIZED":
                self.__parse_msg_parameters(recv_buf, str_count = 0, blob_at_end = False)
                return PrivleapCommServerUnauthorizedMsg()
            else:
                raise ValueError("Invalid message type '" + msg_type_str + "' for socket")

    def __send_msg(self, msg_obj):
        msg_bytes = msg_obj.serialize()
        msg_len_bytes = len(msg_bytes).to_bytes(4, byteorder='big')
        msg_payload = msg_len_bytes + msg_bytes
        msg_payload_sent = 0
        while msg_payload_sent < len(msg_payload):
            msg_sent = self.backend_socket.send(msg_payload[msg_payload_sent:])
            if msg_sent == 0:
                raise ConnectionAbortedError("Connection unexpectedly closed")
            msg_payload_sent += msg_sent

    def send_msg(self, msg_obj):
        if not self.is_session_open:
            raise IOError("Session is closed.")

        msg_obj_type = type(msg_obj)

        if self.is_control_session and self.is_server_side:
            if msg_obj_type != PrivleapControlServerOkMsg \
            and msg_obj_type != PrivleapControlServerControlErrorMsg \
            and msg_obj_type != PrivleapControlServerExistsMsg \
            and msg_obj_type != PrivleapControlServerNouserMsg:
                raise ValueError("Invalid message type for socket.")
        elif self.is_control_session and not self.is_server_side:
            if msg_obj_type != PrivleapControlClientCreateMsg \
            and msg_obj_type != PrivleapControlClientDestroyMsg:
                raise ValueError("Invalid message type for socket.")
        elif not self.is_control_session and self.is_server_side:
            if msg_obj_type != PrivleapCommServerTriggerMsg \
            and msg_obj_type != PrivleapCommServerTriggerErrorMsg \
            and msg_obj_type != PrivleapCommServerResultStdoutMsg \
            and msg_obj_type != PrivleapCommServerResultStderrMsg \
            and msg_obj_type != PrivleapCommServerResultExitcodeMsg \
            and msg_obj_type != PrivleapCommServerUnauthorizedMsg:
                        raise ValueError("Invalid message type for socket.")
        else:
            if msg_obj_type != PrivleapCommClientSignalMsg:
                raise ValueError("Invalid message type for socket.")

        self.__send_msg(msg_obj)

    def close_session(self):
        self.backend_socket.shutdown(socket.SHUT_RDWR)
        self.backend_socket.close()
        self.is_session_open = False

class PrivleapAction:
    action_name = None
    action_command = None
    auth_user = None
    auth_group = None
    target_user = "root"
    target_group = "root"

    def __init__(self, action_name: str = "", action_command: str = "", auth_user: str = "", auth_group: str = "", target_user: str = "", target_group: str = ""):
        if action_name == "":
            raise ValueError("action_name is empty")
        if action_command == "":
            raise ValueError("action_command is empty")
        if target_user == "":
            target_user = "root"
        if target_group == "":
            target_group = "root"

        if not PrivleapCommon.validate_id(action_name, PrivleapValidateType.SIGNAL_NAME):
            raise ValueError("Action name '" + action_name + "' is invalid")

        for key, value in { "auth_user": auth_user,
                            "auth_group": auth_group,
                            "target_user": target_user,
                            "target_group": target_group }.items():
            if not value == "" and not PrivleapCommon.validate_id(value, PrivleapValidateType.USER_GROUP_NAME):
                raise ValueError("Invalid value '" + value + "' for argument '" + key +"'")

        self.action_name = action_name
        self.action_command = action_command
        self.auth_user = auth_user if auth_user != "" else None
        self.auth_group = auth_group if auth_user != "" else None
        self.target_user = target_user
        self.target_group = target_group

class PrivleapCommon:
    state_dir = "/run/privleapd"
    control_path = state_dir + "/control"
    comm_path = state_dir + "/comm"
    config_file_regex = re.compile(r"[-A-Za-z0-9_./]+\.conf\Z")
    user_name_regex = re.compile(r"[A-Za-z_][-A-Za-z0-9_]*\$?\Z")
    signal_name_regex = re.compile(r"[-A-Za-z0-9_.]+\Z")

    @staticmethod
    def validate_id(id_string: str, validate_type: PrivleapValidateType):
        if len(id_string) > 100:
            return False

        if validate_type is PrivleapValidateType.USER_GROUP_NAME:
            if PrivleapCommon.user_name_regex.match(id_string):
                return True
        elif validate_type is PrivleapValidateType.CONFIG_FILE:
            if PrivleapCommon.config_file_regex.match(id_string):
                return True
        elif validate_type is PrivleapValidateType.SIGNAL_NAME:
            if PrivleapCommon.signal_name_regex.match(id_string):
                return True

        return False

    @staticmethod
    def parse_config_file(config_data: str):
        output_list = list()
        conf_stream = StringIO(config_data)
        detect_comment_regex = re.compile(r"\s*#")
        detect_header_regex = re.compile(r"\[.*]\Z")
        current_action_name = ""
        current_action_command = ""
        current_auth_user = ""
        current_auth_group = ""
        current_target_user = ""
        current_target_group = ""
        first_header_parsed = False
        for line in conf_stream:
            line = line.strip()
            if line == "":
                continue

            if detect_comment_regex.match(line):
                continue

            if detect_header_regex.match(line):
                if first_header_parsed:
                    output_list.append(PrivleapAction(current_action_name,
                                                      current_action_command,
                                                      current_auth_user,
                                                      current_auth_group,
                                                      current_target_user,
                                                      current_target_group))
                    # We don't need to zero out current_action_name since we set
                    # its value below.
                    # current_action_name = ""
                    current_action_command = ""
                    current_auth_user = ""
                    current_auth_group = ""
                    current_target_user = ""
                    current_target_group = ""
                else:
                    first_header_parsed = True

                current_action_name = line[1:len(line)-1]
                continue

            line_parts = line.split('=', maxsplit = 1)
            if len(line_parts) != 2:
                raise ValueError("Invalid config line '" + line +"'")

            config_key = line_parts[0]
            config_val = line_parts[1]
            if config_key == "Command":
                current_action_command = config_val
            elif config_key == "AuthorizedUser":
                current_auth_user = config_val
            elif config_key == "AuthorizedGroup":
                current_auth_group = config_val
            elif config_key == "TargetUser":
                current_target_user = config_val
            elif config_key == "TargetGroup":
                current_target_group = config_val
            else:
                raise ValueError("Unrecognized key '" + config_key +"' found")

        # The last action in the file won't be in the list yet, add it now
        output_list.append(PrivleapAction(current_action_name,
                                          current_action_command,
                                          current_auth_user,
                                          current_auth_group,
                                          current_target_user,
                                          current_target_group))

        return output_list
