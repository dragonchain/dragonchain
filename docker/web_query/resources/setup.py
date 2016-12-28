from distutils.spawn import find_executable
from setuptools import setup, find_packages, Command
from glob import glob
import os.path

cmdclass = {}

ROOT = os.path.abspath(os.path.dirname(__file__))
THRIFT = find_executable('thrift1')
if THRIFT is None:
    THRIFT = find_executable('thrift')

# If we have a thrift compiler installed, let's use it to re-generate
# the .py files.  If not, we'll use the pre-generated ones.
if THRIFT is not None:
    class gen_thrift(Command):
        user_options=[]

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            self.mkpath(os.path.join(ROOT, 'blockchain', 'gen'))
            for f in glob(os.path.join(ROOT, 'thrift', '*.thrift')):
                self.spawn([THRIFT, '-out', os.path.join(ROOT, 'blockchain', 'gen'),
                            '-r', '--gen', 'py',
                            os.path.join(ROOT, 'thrift', f)])

    cmdclass['gen_thrift'] = gen_thrift

setup(name         = 'Blockchain',
      version      = '0.0.1',
      description  = 'blockchain stuff',
      author       = 'Folks',
      packages     = ['blockchain'],
      cmdclass     = cmdclass
)
