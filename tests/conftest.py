# -*- coding: utf-8 -*-
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tts_engine.cache_manager import CacheManager


@pytest.fixture
def tmp_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(tmpdir, max_size_mb=1)
        yield cache
