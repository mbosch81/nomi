import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch
from nomi.core import Settings, AnalysisCancelled
from nomi.llama_backend import LocalEngine, local_request

# A real child HTTP server exercises ownership, startup, auth and cleanup without weights.
RUNTIME = '''import os,sys,time,json
from http.server import BaseHTTPRequestHandler,HTTPServer
args=sys.argv
port=int(args[args.index('--port')+1])
model=args[args.index('--model')+1]
if 'crash' in model:sys.exit(2)
if 'slow' in model:time.sleep(30)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,data,status=200):
  self.send_response(status);self.end_headers();self.wfile.write(json.dumps(data).encode())
 def do_GET(self):
  if self.headers.get('Authorization')!='Bearer '+os.environ['LLAMA_API_KEY']:
   self.send({},401);return
  self.send({'status':'ok'} if self.path=='/health' else {'data':[{'id':'nomi-local'}]})
 def do_POST(self):
  if self.headers.get('Authorization')!='Bearer '+os.environ['LLAMA_API_KEY']:
   self.send({},401);return
  data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  assert data['response_format']['json_schema']['schema']['type']=='object'
  assert data['chat_template_kwargs']['enable_thinking']==False
  content=json.dumps({'datum':'14.10.2026','absender':'Beispiel GmbH','dokumenttyp':'Rechnung'})
  self.send({'choices':[{'message':{'content':content},'finish_reason':'stop'}]})
HTTPServer(('127.0.0.1',port),Handler).serve_forever()
'''


@unittest.skipIf(sys.platform=='win32', 'POSIX executable fixture')
class LocalEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.runtime=self.root/'runtime'
        self.runtime.write_text(f'#!{sys.executable}\n'+RUNTIME);self.runtime.chmod(0o700)
        self.model=self.root/'model.gguf';self.model.write_bytes(b'GGUFtest')
        self.engine=LocalEngine();self.addCleanup(self.engine.stop)

    def test_real_child_auth_structured_generation_reuse_and_shutdown(self):
        backend=self.engine.start(self.model, executable=self.runtime)
        process=self.engine._process
        with patch.dict(os.environ, {'http_proxy':'http://127.0.0.1:1','HTTP_PROXY':'http://127.0.0.1:1'}):
            data=backend.suggest('Rechnungsdatum: 14.10.2026',Settings())
        self.assertEqual(data['datum'],'2026-10-14')
        with self.assertRaises(OSError):local_request(backend.url,'wrong-key','/v1/models')
        self.assertIs(self.engine.start(self.model,executable=self.runtime),backend)
        self.assertIs(self.engine._process,process)
        self.engine.stop()
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.engine.alive())

    def test_cancel_and_timeout_terminate_starting_child(self):
        model=self.root/'slow.gguf';model.write_bytes(b'GGUFtest')
        processes=[];real_popen=subprocess.Popen
        def start(*args,**kwargs):
            child=real_popen(*args,**kwargs);processes.append(child);return child
        with patch('nomi.llama_backend.subprocess.Popen',side_effect=start):
            began=time.monotonic()
            with self.assertRaises(AnalysisCancelled):
                self.engine.start(model,lambda:time.monotonic()-began>.2,executable=self.runtime)
            with self.assertRaises(TimeoutError):
                self.engine.start(model,executable=self.runtime,startup_timeout=.2)
        self.assertEqual(len(processes),2)
        self.assertTrue(all(child.poll() is not None for child in processes))
        self.assertFalse(self.engine.alive())

    def test_failed_start_and_invalid_gguf_are_reported(self):
        bad=self.root/'bad.gguf';bad.write_bytes(b'not a GGUF')
        with self.assertRaisesRegex(ValueError,'GGUF'):
            self.engine.start(bad,executable=self.runtime)
        crash=self.root/'crash.gguf';crash.write_bytes(b'GGUFtest')
        with self.assertRaisesRegex(ValueError,'nicht laden'):
            self.engine.start(crash,executable=self.runtime)
        self.assertFalse(self.engine.alive())

    def test_selecting_another_model_stops_previous_process(self):
        self.engine.start(self.model,executable=self.runtime)
        previous=self.engine._process
        other=self.root/'other.gguf';other.write_bytes(b'GGUFother')
        self.engine.start(other,executable=self.runtime)
        self.assertIsNotNone(previous.poll())
        self.assertNotEqual(self.engine._process.pid,previous.pid)
        self.assertEqual(self.engine.model,other)
