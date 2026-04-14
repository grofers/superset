
import logging
import pickle
import sys
from typing import Any, Optional

from flask import Flask, has_request_context, request
from flask_caching.backends.rediscache import RedisClusterCache

from superset.constants import CacheRegion

logger = logging.getLogger(__name__)

# Cache type for metrics - extends CacheRegion with additional types
CACHE_TYPE_UNKNOWN = "unknown"


class RedisClusterCacheWithMetrics(RedisClusterCache):
    """
    Redis cluster cache backend that tracks data size metrics.
    
    This wrapper tracks the size of data fetched from Redis and pushes
    metrics to StatsD with labels for dashboard_id and chart_id to enable
    debugging of high network consuming dashboards.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stats_logger = None

    def init_app(
        self, app: Flask, config: Optional[dict[str, Any]] = None
    ) -> None:
        super().init_app(app, config)
        
        if app and hasattr(app, "config"):
            self._stats_logger = app.config.get("STATS_LOGGER")

    def _get_context_labels(self, key: str) -> dict[str, str]:
        """
        Extract context labels from cache key and request context.

        Args:
            key: Cache key

        Returns:
            Dictionary with dashboard_id, chart_id, and cache_type labels
        """
        labels = {
            "dashboard_id": CACHE_TYPE_UNKNOWN,
            "chart_id": CACHE_TYPE_UNKNOWN,
            "cache_type": CACHE_TYPE_UNKNOWN,
        }

        # Determine cache type from key prefix
        if key:
            if key.startswith("superset:thumbnail:"):
                labels["cache_type"] = CacheRegion.THUMBNAIL.value
            elif "ejr-" in key or "qc-" in key:
                # Query cache keys (explore_json_request or query_context)
                labels["cache_type"] = CacheRegion.DATA.value
            elif key.startswith("superset:dc:"):
                # Data cache prefix
                labels["cache_type"] = CacheRegion.DATA.value
            elif key.startswith("superset:"):
                # General superset cache
                labels["cache_type"] = CacheRegion.DEFAULT.value

        
        if has_request_context():
            try:
                
                if hasattr(request, "args"):
                    dashboard_id = request.args.get("dashboard_id")
                    if dashboard_id:
                        labels["dashboard_id"] = str(dashboard_id)

                
                if hasattr(request, "args"):
                    chart_id = request.args.get("slice_id") or request.args.get("chart_id")
                    if chart_id:
                        labels["chart_id"] = str(chart_id)

                
                if hasattr(request, "json") and request.json:
                    json_data = request.json
                    if isinstance(json_data, dict):
                        if "dashboard_id" in json_data:
                            labels["dashboard_id"] = str(json_data["dashboard_id"])
                        if "slice_id" in json_data:
                            labels["chart_id"] = str(json_data["slice_id"])
                        if "chart_id" in json_data:
                            labels["chart_id"] = str(json_data["chart_id"])
                        
                        if "form_data" in json_data and isinstance(json_data["form_data"], dict):
                            form_data = json_data["form_data"]
                            if "slice_id" in form_data:
                                labels["chart_id"] = str(form_data["slice_id"])

                
                if hasattr(request, "path"):
                    path = request.path
                    
                    if "/chart/" in path:
                        parts = path.split("/chart/")
                        if len(parts) > 1:
                            chart_part = parts[1].split("/")[0]
                            if chart_part.isdigit():
                                labels["chart_id"] = chart_part
                    
                    if "/dashboard/" in path:
                        parts = path.split("/dashboard/")
                        if len(parts) > 1:
                            dashboard_part = parts[1].split("/")[0]
                            if dashboard_part.isdigit():
                                labels["dashboard_id"] = dashboard_part

            except Exception as ex:  
                
                logger.debug("Error extracting context labels: %s", ex)

        return labels

    def _calculate_size(self, value: Any) -> int:
        try:
            if value is None:
                return 0
            
            
            return sys.getsizeof(pickle.dumps(value))
        except Exception as ex:  
            logger.debug("Error calculating cache value size: %s", ex)
            return 0

    def _push_metrics(self, key: str, data_size: int, operation: str = "get") -> None:
        if not self._stats_logger:
            
            try:
                from flask import current_app
                if hasattr(current_app, "config"):
                    self._stats_logger = current_app.config.get("STATS_LOGGER")
            except Exception:  
                pass

            if not self._stats_logger:
                return

        try:
            labels = self._get_context_labels(key)
            metric_base = f"redis.cache.{operation}"
            size_metric = f"{metric_base}.data_size_bytes"
            self._stats_logger.gauge(size_metric, data_size)
            labeled_metric = (
                f"{metric_base}.{labels['cache_type']}"
                f".dashboard_{labels['dashboard_id']}"
                f".chart_{labels['chart_id']}"
            )
            self._stats_logger.gauge(labeled_metric, data_size)

            
            counter_metric = f"{metric_base}.count.{labels['cache_type']}"
            self._stats_logger.incr(counter_metric)

            logger.debug(
                "Pushed cache metrics: %s, size=%d bytes, labels=%s",
                operation,
                data_size,
                labels,
            )
        except Exception as ex:  
            
            logger.debug("Error pushing cache metrics: %s", ex)

    def get(self, key: str) -> Any:
        value = super().get(key)

        if value is not None:
            
            data_size = self._calculate_size(value)
            self._push_metrics(key, data_size, operation="get")

        return value

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        result = super().set(key, value, timeout)

        if result:
            
            data_size = self._calculate_size(value)
            self._push_metrics(key, data_size, operation="set")

        return result
