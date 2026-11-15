import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ebtime_installer',root/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
class Installation(unittest.TestCase):
    def test_install_backup_and_paths(self):
        with tempfile.TemporaryDirectory(prefix="ebtime 'test ") as d:
            fusion=Path(d)/'Fusion';python,appdir=installer.install(fusion,skip_dependencies=True)
            self.assertTrue((appdir/'ebtime_core.py').exists());self.assertTrue((appdir/'app.py').exists())
            self.assertEqual(json.loads((appdir/'runtime.json').read_text())['python'],str(python))
            entry=(fusion/'Scripts/Comp/ebtime Editor.py').read_text()
            self.assertNotIn('Path(__file__)',entry);compile(entry,'entry','exec')
            text=(fusion/'Templates/Edit/Effects/ebtime/ebtime.setting').read_text()
            self.assertIn('ebtime Editor.py',text);self.assertNotIn('Scripts:Comp',text)
            installer.install(fusion,skip_dependencies=True)
            self.assertTrue((fusion/'Macros/ebtime.setting.bak').exists())

if __name__=='__main__':unittest.main()
