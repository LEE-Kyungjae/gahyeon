import io
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from scripts import macos_core_connection as connection


class MacosCoreTunnelTest(unittest.TestCase):
    def test_occupied_port_is_not_treated_as_authenticated_core(self):
        with socket.socket() as foreign:
            foreign.bind(('127.0.0.1', 0)); foreign.listen()
            port = foreign.getsockname()[1]
            self.assertNotEqual(connection.available_port(port), port)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True), \
                patch.object(connection, 'available_port', return_value=23456), \
                patch.object(connection.subprocess, 'run') as ssh, \
                patch.object(connection, 'speech_status', return_value={'transcriptionReady': True, 'synthesisReady': True}) as status:
            url, _ = connection.connect_land_core('fixture', folder)
            self.assertEqual(url, 'http://127.0.0.1:23456/api')
            self.assertIn('127.0.0.1:23456:127.0.0.1:18080', ssh.call_args.args[0])
            self.assertNotIn('fixture', ' '.join(ssh.call_args.args[0]))
            status.assert_called_once_with(url, 'fixture')
            self.assertEqual(json.loads((Path(folder)/'land-core-connection.json').read_text()), {'port':23456})

    def test_rejects_unrelated_http_service(self):
        with patch.object(connection.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"healthy":true}')):
            with self.assertRaisesRegex(RuntimeError, 'not the Gahyeon'):
                connection.speech_status('http://127.0.0.1:23456/api', 'fixture')

    def test_explicit_endpoint_never_silently_switches(self):
        with patch.dict(os.environ, {'GAHYEON_CORE_URL':'http://127.0.0.1:23456/api'}), \
                patch.object(connection, 'speech_status', side_effect=RuntimeError('not ready')), \
                patch.object(connection.subprocess, 'run') as ssh:
            with self.assertRaisesRegex(RuntimeError, 'not ready'):
                connection.connect_land_core('fixture')
            ssh.assert_not_called()


if __name__ == '__main__': unittest.main()
