"""
Copyright 2016 Disney Connected and Advanced Technologies

Licensed under the Apache License, Version 2.0 (the "Apache License")
with the following modification; you may not use this file except in
compliance with the Apache License and the following modification to it:
Section 6. Trademarks. is deleted and replaced with:

     6. Trademarks. This License does not grant permission to use the trade
        names, trademarks, service marks, or product names of the Licensor
        and its affiliates, except as required to comply with Section 4(c) of
        the License and to reproduce the content of the NOTICE file.

You may obtain a copy of the Apache License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the Apache License with the above modification is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied. See the Apache License for the specific
language governing permissions and limitations under the Apache License.
"""

__author__ = "Joe Roets, Brandon Kite, Dylan Yelton, Michael Bachtel"
__copyright__ = "Copyright 2016, Disney Connected and Advanced Technologies"
__license__ = "Apache"
__version__ = "2.0"
__maintainer__ = "Joe Roets"
__email__ = "joe@dragonchain.org"

from distutils.errors import DistutilsError
from distutils.spawn import find_executable
from setuptools import setup, Command
from glob import glob
import os.path

# If we have a thrift compiler installed, let's use it to re-generate
# the .py files.  If not, we'll use the pre-generated ones.
class gen_thrift(Command):
    user_options=[]

    def initialize_options(self):
        self.root = None
        self.thrift = None

    def finalize_options(self):
        self.root = os.path.abspath(os.path.dirname(__file__))
        self.thrift = find_executable('thrift1')
        if self.thrift is None:
            self.thrift = find_executable('thrift')

    def run(self):
        if self.thrift is None:
            raise DistutilsError(
                'Apache Thrift binary not found.  Please install Apache Thrift or use pre-generated Thrift classes.')

        self.mkpath(os.path.join(self.root, 'blockchain', 'gen'))
        for f in glob(os.path.join(self.root, 'thrift', '*.thrift')):
            self.spawn([self.thrift, '-out', os.path.join(self.root, 'blockchain', 'gen'),
                        '-r', '--gen', 'py',
                        os.path.join(self.root, 'thrift', f)])

setup(name         = 'Blockchain',
      version      = '0.0.2',
      description  = 'blockchain stuff',
      author       = 'Folks',
      packages     = ['blockchain'],
      cmdclass     = {
          'gen_thrift': gen_thrift
      }
)
