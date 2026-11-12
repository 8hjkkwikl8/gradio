import urllib.parse

import pytest

import gradio as gr
from gradio import http_server, routes


def test_windows_excluded_port_error_mentions_reserved_ranges():
    message = http_server._port_error_message(
        [7865], OSError(10013, "Permission denied"), platform="win32"
    )
    assert "Cannot find empty port in range: 7865-7865" in message
    assert "excluded port range" in message
    assert "netsh int ipv4 show excludedportrange protocol=tcp" in message


def test_port_error_stays_generic_outside_windows():
    message = http_server._port_error_message(
        [7865], OSError(10013, "Permission denied"), platform="linux"
    )
    assert "Cannot find empty port in range: 7865-7865" in message
    assert "excluded port range" not in message


def test_start_server_chains_last_bind_error(monkeypatch):
    class DeniedSocket:
        def setsockopt(self, *args):
            pass

        def bind(self, address):
            raise OSError(10013, "Permission denied")

        def close(self):
            pass

    monkeypatch.setattr(http_server.socket, "socket", DeniedSocket)
    with pytest.raises(OSError) as excinfo:
        http_server.start_server(app=None, server_port=7865)  # type: ignore[arg-type]
    assert isinstance(excinfo.value.__cause__, OSError)
    assert "Cannot find empty port in range: 7865-7865" in str(excinfo.value)


class TestStartServer:
    # Test IPv4 and IPv6 hostnames as they would be passed from --server-name.
    @pytest.mark.parametrize("host", ["127.0.0.1", "[::1]"])
    def test_start_server(self, host):
        io = gr.Interface(lambda x: x, "number", "number")
        io.favicon_path = None
        io.config = io.get_config_file()
        io.show_error = True
        io.flagging_callback.setup([gr.Number()], io.flagging_dir)
        io.auth = None
        app = routes.App.create_app(io)

        _, _, local_path, server = http_server.start_server(app)
        url = urllib.parse.urlparse(local_path)
        assert url.scheme == "http"
        assert url.port is not None
        assert (
            http_server.INITIAL_PORT_VALUE
            <= url.port
            <= http_server.INITIAL_PORT_VALUE + http_server.TRY_NUM_PORTS
        )
        server.close()
