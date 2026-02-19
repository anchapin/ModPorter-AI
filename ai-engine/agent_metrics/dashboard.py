"""
Metrics Dashboard for aggregating and exporting metrics
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .performance_monitor import performance_tracker
from .llm_usage_tracker import llm_tracker
from .memory_monitor import memory_monitor
from .alerts import alert_manager

logger = logging.getLogger(__name__)


class MetricsDashboard:
    """
    Aggregates metrics from all monitors for dashboard display.
    
    Features:
    - Combined metrics from all trackers
    - JSON export for APIs
    - Prometheus export for monitoring systems
    - Health status checks
    """
    
    def __init__(self):
        """Initialize the metrics dashboard"""
        self._start_time = datetime.now()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics combined.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
            'performance': self._get_performance_metrics(),
            'llm_usage': self._get_llm_metrics(),
            'memory': self._get_memory_metrics(),
            'alerts': self._get_alert_metrics(),
            'health': self._get_health_status()
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            return {
                'summary': performance_tracker.get_summary(),
                'metrics': performance_tracker.get_metrics(),
                'recent_operations': performance_tracker.get_recent_operations(limit=20)
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {'error': str(e)}
    
    def _get_llm_metrics(self) -> Dict[str, Any]:
        """Get LLM usage metrics"""
        try:
            return {
                'total_usage': llm_tracker.get_total_usage(),
                'usage_by_model': llm_tracker.get_usage_by_model(),
                'cost_breakdown': llm_tracker.get_cost_breakdown(),
                'recent_calls': llm_tracker.get_recent_calls(limit=20)
            }
        except Exception as e:
            logger.error(f"Error getting LLM metrics: {e}")
            return {'error': str(e)}
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory metrics"""
        try:
            return {
                'current_usage': memory_monitor.get_current_usage(),
                'peak_usage': memory_monitor.get_peak_usage(),
                'memory_growth': memory_monitor.get_memory_growth(),
                'history': memory_monitor.get_memory_history(limit=20),
                'top_consumers': memory_monitor.get_top_memory_consumers()
            }
        except Exception as e:
            logger.error(f"Error getting memory metrics: {e}")
            return {'error': str(e)}
    
    def _get_alert_metrics(self) -> Dict[str, Any]:
        """Get alert metrics"""
        try:
            return {
                'summary': alert_manager.get_alert_summary(),
                'recent_alerts': alert_manager.get_alerts(limit=20),
                'thresholds': alert_manager.get_thresholds()
            }
        except Exception as e:
            logger.error(f"Error getting alert metrics: {e}")
            return {'error': str(e)}
    
    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status.
        
        Returns:
            Health status with checks
        """
        health = {
            'status': 'healthy',
            'checks': {}
        }
        
        # Check memory
        try:
            memory = memory_monitor.get_current_usage()
            thresholds = alert_manager.get_thresholds()
            
            if memory['rss_mb'] >= thresholds['memory_critical']:
                health['checks']['memory'] = 'critical'
                health['status'] = 'unhealthy'
            elif memory['rss_mb'] >= thresholds['memory_warning']:
                health['checks']['memory'] = 'warning'
                if health['status'] == 'healthy':
                    health['status'] = 'degraded'
            else:
                health['checks']['memory'] = 'ok'
        except Exception:
            health['checks']['memory'] = 'unknown'
        
        # Check error rate
        try:
            perf_summary = performance_tracker.get_summary()
            total = perf_summary.get('total_operations', 0)
            failed = perf_summary.get('failed_operations', 0)
            
            if total > 0:
                error_rate = failed / total
                if error_rate >= alert_manager.get_thresholds()['error_rate']:
                    health['checks']['error_rate'] = 'critical'
                    health['status'] = 'unhealthy'
                else:
                    health['checks']['error_rate'] = 'ok'
            else:
                health['checks']['error_rate'] = 'ok'
        except Exception:
            health['checks']['error_rate'] = 'unknown'
        
        # Check LLM availability
        try:
            llm_usage = llm_tracker.get_total_usage()
            if llm_usage.get('total_calls', 0) > 0:
                success_rate = llm_usage.get('successful_calls', 0) / llm_usage['total_calls']
                if success_rate < 0.5:
                    health['checks']['llm'] = 'degraded'
                    if health['status'] == 'healthy':
                        health['status'] = 'degraded'
                else:
                    health['checks']['llm'] = 'ok'
            else:
                health['checks']['llm'] = 'ok'
        except Exception:
            health['checks']['llm'] = 'unknown'
        
        # Check for unacknowledged alerts
        try:
            alert_summary = alert_manager.get_alert_summary()
            unacknowledged = alert_summary.get('unacknowledged', 0)
            if unacknowledged > 5:
                health['checks']['alerts'] = 'warning'
                if health['status'] == 'healthy':
                    health['status'] = 'degraded'
            else:
                health['checks']['alerts'] = 'ok'
        except Exception:
            health['checks']['alerts'] = 'unknown'
        
        return health
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a concise summary of key metrics.
        
        Returns:
            Summary dictionary
        """
        try:
            perf = performance_tracker.get_summary()
            llm = llm_tracker.get_total_usage()
            mem = memory_monitor.get_current_usage()
            alerts = alert_manager.get_alert_summary()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
                'operations': {
                    'total': perf.get('total_operations', 0),
                    'success_rate': perf.get('success_rate', 0)
                },
                'llm': {
                    'calls': llm.get('total_calls', 0),
                    'tokens': llm.get('total_tokens', 0),
                    'cost': llm.get('total_cost', 0)
                },
                'memory': {
                    'current_mb': mem.get('rss_mb', 0),
                    'percent': mem.get('percent', 0)
                },
                'alerts': {
                    'total': alerts.get('total_alerts', 0),
                    'unacknowledged': alerts.get('unacknowledged', 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {'error': str(e)}
    
    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = [
            '# ModPorter AI Engine Metrics',
            '# Generated at', datetime.now().isoformat(),
            ''
        ]
        
        # Performance metrics
        lines.append('# Performance Metrics')
        lines.append(performance_tracker.export_prometheus())
        lines.append('')
        
        # LLM metrics
        lines.append('# LLM Usage Metrics')
        lines.append(llm_tracker.export_prometheus())
        lines.append('')
        
        # Memory metrics
        lines.append('# Memory Metrics')
        lines.append(memory_monitor.export_prometheus())
        lines.append('')
        
        # Alert metrics
        lines.append('# Alert Metrics')
        alert_summary = alert_manager.get_alert_summary()
        lines.append(f'# HELP alerts_total Total alerts')
        lines.append(f'# TYPE alerts_total counter')
        lines.append(f'alerts_total {alert_summary.get("total_alerts", 0)}')
        lines.append(f'# HELP alerts_unacknowledged Unacknowledged alerts')
        lines.append(f'# TYPE alerts_unacknowledged gauge')
        lines.append(f'alerts_unacknowledged {alert_summary.get("unacknowledged", 0)}')
        
        return '\n'.join(lines)
    
    def export_json(self, indent: int = 2) -> str:
        """
        Export all metrics as JSON.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string
        """
        return json.dumps(self.get_all_metrics(), indent=indent, default=str)
    
    def reset_all(self):
        """Reset all metrics"""
        performance_tracker.reset()
        llm_tracker.reset()
        memory_monitor.clear_history()
        alert_manager.clear_alerts()
        self._start_time = datetime.now()
        logger.info("All metrics reset")


# Global functions for easy access
_dashboard = MetricsDashboard()


def get_dashboard_data() -> Dict[str, Any]:
    """Get all dashboard data"""
    return _dashboard.get_all_metrics()


def export_metrics(format: str = 'json') -> str:
    """
    Export metrics in the specified format.
    
    Args:
        format: 'json' or 'prometheus'
        
    Returns:
        Formatted metrics string
    """
    if format == 'prometheus':
        return _dashboard.export_prometheus()
    else:
        return _dashboard.export_json()