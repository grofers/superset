# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Tests for Redis cache metrics tracking."""
from unittest.mock import MagicMock, patch

import pytest

from superset.constants import CacheRegion
from superset.extensions.redis_cache_with_metrics import (
    CACHE_TYPE_UNKNOWN,
    RedisCacheWithMetrics,
)


class TestRedisCacheWithMetrics:
    """Test suite for Redis cache metrics functionality."""

    def test_get_context_labels_from_cache_key(self):
        """Test extracting cache type from cache key."""
        cache = RedisCacheWithMetrics()

        # Test thumbnail cache
        labels = cache._get_context_labels("superset:thumbnail:abc123")
        assert labels["cache_type"] == CacheRegion.THUMBNAIL.value

        # Test data cache (dc: prefix)
        labels = cache._get_context_labels("superset:dc:qc-xyz789")
        assert labels["cache_type"] == CacheRegion.DATA.value

        # Test data cache (qc- in key)
        labels = cache._get_context_labels("qc-xyz789")
        assert labels["cache_type"] == CacheRegion.DATA.value

        # Test default/general cache
        labels = cache._get_context_labels("superset:general:test")
        assert labels["cache_type"] == CacheRegion.DEFAULT.value

        # Test unknown cache type
        labels = cache._get_context_labels("random:key")
        assert labels["cache_type"] == CACHE_TYPE_UNKNOWN

    @patch("superset.extensions.redis_cache_with_metrics.has_request_context")
    @patch("superset.extensions.redis_cache_with_metrics.request")
    def test_get_context_labels_from_request_args(
        self, mock_request, mock_has_request_context
    ):
        """Test extracting labels from request arguments."""
        mock_has_request_context.return_value = True
        mock_request.args = {"dashboard_id": "123", "slice_id": "456"}
        mock_request.json = None
        mock_request.path = "/api/v1/test"
        
        cache = RedisCacheWithMetrics()
        labels = cache._get_context_labels("test_key")
        
        assert labels["dashboard_id"] == "123"
        assert labels["chart_id"] == "456"

    @patch("superset.extensions.redis_cache_with_metrics.has_request_context")
    @patch("superset.extensions.redis_cache_with_metrics.request")
    def test_get_context_labels_from_request_json(
        self, mock_request, mock_has_request_context
    ):
        """Test extracting labels from request JSON body."""
        mock_has_request_context.return_value = True
        mock_request.args = {}
        mock_request.json = {
            "dashboard_id": 789,
            "form_data": {"slice_id": 101}
        }
        mock_request.path = "/api/v1/test"
        
        cache = RedisCacheWithMetrics()
        labels = cache._get_context_labels("test_key")
        
        assert labels["dashboard_id"] == "789"
        assert labels["chart_id"] == "101"

    @patch("superset.extensions.redis_cache_with_metrics.has_request_context")
    @patch("superset.extensions.redis_cache_with_metrics.request")
    def test_get_context_labels_from_url_path(
        self, mock_request, mock_has_request_context
    ):
        """Test extracting labels from URL path."""
        mock_has_request_context.return_value = True
        mock_request.args = {}
        mock_request.json = None
        mock_request.path = "/api/v1/chart/999/data"
        
        cache = RedisCacheWithMetrics()
        labels = cache._get_context_labels("test_key")
        
        assert labels["chart_id"] == "999"

    def test_calculate_size(self):
        """Test size calculation for cached values."""
        cache = RedisCacheWithMetrics()
        
        # Test None
        assert cache._calculate_size(None) == 0
        
        # Test string
        size = cache._calculate_size("test string")
        assert size > 0
        
        # Test dict
        size = cache._calculate_size({"key": "value", "number": 123})
        assert size > 0

    @patch.object(RedisCacheWithMetrics, "_push_metrics")
    @patch("flask_caching.backends.rediscache.RedisCache.get")
    def test_get_with_metrics(self, mock_super_get, mock_push_metrics):
        """Test that get operation pushes metrics."""
        cache = RedisCacheWithMetrics()
        test_value = {"data": "test"}
        mock_super_get.return_value = test_value
        
        result = cache.get("test_key")
        
        assert result == test_value
        mock_push_metrics.assert_called_once()
        call_args = mock_push_metrics.call_args
        assert call_args[0][0] == "test_key"  # key
        assert call_args[0][1] > 0  # data_size
        assert call_args[0][2] == "get"  # operation

    @patch.object(RedisCacheWithMetrics, "_push_metrics")
    @patch("flask_caching.backends.rediscache.RedisCache.set")
    def test_set_with_metrics(self, mock_super_set, mock_push_metrics):
        """Test that set operation pushes metrics."""
        cache = RedisCacheWithMetrics()
        test_value = {"data": "test"}
        mock_super_set.return_value = True
        
        result = cache.set("test_key", test_value)
        
        assert result is True
        mock_push_metrics.assert_called_once()
        call_args = mock_push_metrics.call_args
        assert call_args[0][0] == "test_key"  # key
        assert call_args[0][1] > 0  # data_size
        assert call_args[0][2] == "set"  # operation

    def test_push_metrics(self):
        """Test metrics pushing to StatsD."""
        cache = RedisCacheWithMetrics()
        mock_stats_logger = MagicMock()
        cache._stats_logger = mock_stats_logger
        
        cache._push_metrics("test_key", 1024, "get")
        
        # Verify gauge was called for data size
        assert mock_stats_logger.gauge.called
        
        # Verify incr was called for counter
        assert mock_stats_logger.incr.called

