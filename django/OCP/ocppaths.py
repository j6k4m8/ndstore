# Copyright 2014 Open Connectome Project (http://openconnecto.me)
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Code to load project paths
#

import os, sys

OCP_BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.." ))
OCP_UTIL_PATH = os.path.join(OCP_BASE_PATH, "util" )
OCP_OCPCA_PATH = os.path.join(OCP_BASE_PATH, "ocpca" )
OCP_STATS_PATH = os.path.join(OCP_BASE_PATH, "stats" )
OCP_OCPLIB_PATH = os.path.join(OCP_BASE_PATH, "ocplib" )
OCP_DJANGO_PATH = os.path.join(OCP_BASE_PATH, "django" )

sys.path += [ OCP_UTIL_PATH, OCP_OCPCA_PATH, OCP_STATS_PATH, OCP_OCPLIB_PATH, OCP_DJANGO_PATH ]

