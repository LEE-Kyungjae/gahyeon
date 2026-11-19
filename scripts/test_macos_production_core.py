import base64
import os
import tempfile
import unittest
from unittest.mock import patch
from scripts import macos_production_core as core

class ProductionCoreConnectionTest(unittest.TestCase):
    def test_production_uses_zeze_and_never_places_credential_in_ssh_or_state(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{},clear=True), \
                patch.object(core.subprocess,'check_output',side_effect=[base64.b64encode(b'fixture-secret').decode(),'10.43.1.2']), \
                patch.object(core.subprocess,'run') as run, patch.object(core,'available_port',return_value=23456), \
                patch.object(core,'speech_status',return_value={'transcriptionReady':True}) as status:
            url, token, _=core.connect_production_core(folder)
            self.assertEqual(url,'http://127.0.0.1:23456/api')
            self.assertEqual(token,'fixture-secret')
            command=run.call_args.args[0]
            self.assertEqual(command[-1],'zeze')
            self.assertIn('127.0.0.1:23456:10.43.1.2:8080',command)
            self.assertNotIn(token,' '.join(command))
            self.assertNotIn(token,(core.Path(folder)/'zeze-core-connection.json').read_text())
            status.assert_called_once_with(url,token)

    def test_explicit_qa_endpoint_does_not_read_production_credentials(self):
        with patch.dict(os.environ,{'GAHYEON_CORE_URL':'http://127.0.0.1:18083/api','GAHYEON_CLIENT_TOKEN':'qa'},clear=True), \
                patch.object(core.subprocess,'check_output') as ssh, patch.object(core,'speech_status',return_value={}):
            self.assertEqual(core.connect_production_core()[:2],('http://127.0.0.1:18083/api','qa'))
            ssh.assert_not_called()

if __name__=='__main__': unittest.main()
