from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

# These fixtures administer only the disposable local teaching database.
import os
from urllib.parse import urlparse
from dotenv import dotenv_values
import pytest
config=dotenv_values(Path(__file__).resolve().parents[2]/'.env')
for name in ('DATABASE_URL','ADMIN_DATABASE_URL'):
    value=os.environ.get(name,config.get(name,''))
    if urlparse(value).hostname not in ('localhost','127.0.0.1'):
        raise pytest.UsageError('Integration fixtures are restricted to the local teaching database.')
