#!/usr/bin/env python3
"""
🏥 Health Check Script для Anonymeme Platform
Comprehensive health monitoring для all environments
"""

import asyncio
import aiohttp
import time
import logging
import json
import sys
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health check result for a specific service"""
    service: str
    endpoint: str
    healthy: bool
    response_time_ms: float = 0.0
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SystemHealth:
    """Overall system health status"""
    environment: str
    overall_healthy: bool
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    check_duration_ms: float = 0.0
    results: List[HealthCheckResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class HealthChecker:
    """
    Comprehensive health checker для Anonymeme Platform
    """
    
    def __init__(self, environment: str, timeout: int = 30):
        self.environment = environment
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Service endpoints based on environment
        self.endpoints = self._get_endpoints()
        
        logger.info(f"Initialized health checker for {environment}")
    
    def _get_endpoints(self) -> Dict[str, str]:
        """Get service endpoints based on environment"""
        if self.environment == 'production':
            return {
                'backend_api': 'https://api.anonymeme.io',
                'frontend': 'https://anonymeme.io',
                'websocket': 'wss://ws.anonymeme.io',
                'monitoring': 'https://monitoring.anonymeme.io',
                'load_balancer': 'https://lb.anonymeme.io'
            }
        elif self.environment == 'staging':
            return {
                'backend_api': 'https://staging-api.anonymeme.io',
                'frontend': 'https://staging.anonymeme.io',
                'websocket': 'wss://staging-ws.anonymeme.io',
                'monitoring': 'https://staging-monitoring.anonymeme.io',
                'load_balancer': 'https://staging-lb.anonymeme.io'
            }
        else:  # development
            return {
                'backend_api': 'http://localhost:8000',
                'frontend': 'http://localhost:3000',
                'websocket': 'ws://localhost:8001',
                'monitoring': 'http://localhost:3001',
                'load_balancer': 'http://localhost:80'
            }
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        start_time = time.time()
        logger.info(f"🏥 Starting health check for {self.environment} environment")
        
        # Run all health checks concurrently
        health_checks = [
            # Core services
            self._check_backend_health(),
            self._check_frontend_health(),
            self._check_websocket_health(),
            
            # API endpoints
            self._check_api_endpoints(),
            self._check_authentication_flow(),
            
            # Database connectivity
            self._check_database_health(),
            self._check_redis_health(),
            
            # External dependencies
            self._check_solana_connectivity(),
            self._check_external_services(),
            
            # Performance checks
            self._check_response_times(),
            self._check_resource_usage(),
            
            # Security checks
            self._check_security_headers(),
            self._check_ssl_certificates(),
            
            # Monitoring
            self._check_monitoring_systems(),
        ]
        
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        # Process results
        all_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                all_results.append(HealthCheckResult(
                    service="unknown",
                    endpoint="unknown",
                    healthy=False,
                    error_message=str(result)
                ))
            elif isinstance(result, list):
                all_results.extend(result)
            else:
                all_results.append(result)
        
        # Calculate overall health
        total_checks = len(all_results)
        passed_checks = sum(1 for r in all_results if r.healthy)
        failed_checks = total_checks - passed_checks
        overall_healthy = failed_checks == 0
        
        duration_ms = (time.time() - start_time) * 1000
        
        system_health = SystemHealth(
            environment=self.environment,
            overall_healthy=overall_healthy,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            check_duration_ms=duration_ms,
            results=all_results
        )
        
        logger.info(f"🏥 Health check completed: {passed_checks}/{total_checks} passed")
        return system_health
    
    async def _check_backend_health(self) -> HealthCheckResult:
        """Check backend API health"""
        endpoint = f"{self.endpoints['backend_api']}/health"
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    return HealthCheckResult(
                        service="backend_api",
                        endpoint=endpoint,
                        healthy=True,
                        response_time_ms=response_time,
                        status_code=response.status,
                        details=data
                    )
                else:
                    return HealthCheckResult(
                        service="backend_api",
                        endpoint=endpoint,
                        healthy=False,
                        response_time_ms=response_time,
                        status_code=response.status,
                        error_message=f"Unexpected status code: {response.status}"
                    )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="backend_api",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_frontend_health(self) -> HealthCheckResult:
        """Check frontend health"""
        endpoint = self.endpoints['frontend']
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                healthy = response.status == 200
                return HealthCheckResult(
                    service="frontend",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status,
                    error_message=None if healthy else f"Status: {response.status}"
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="frontend",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_websocket_health(self) -> HealthCheckResult:
        """Check WebSocket health"""
        # For WebSocket health, we'll check if the endpoint responds
        # In a real implementation, this would establish a WebSocket connection
        
        endpoint = self.endpoints['websocket'].replace('ws://', 'http://').replace('wss://', 'https://')
        start_time = time.time()
        
        try:
            async with self.session.get(f"{endpoint}/health") as response:
                response_time = (time.time() - start_time) * 1000
                
                healthy = response.status == 200
                return HealthCheckResult(
                    service="websocket",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="websocket",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_api_endpoints(self) -> List[HealthCheckResult]:
        """Check critical API endpoints"""
        base_url = self.endpoints['backend_api']
        endpoints = [
            '/api/v1/tokens',
            '/api/v1/analytics/tokens',
            '/metrics',
            '/docs'
        ]
        
        results = []
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            start_time = time.time()
            
            try:
                async with self.session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    healthy = response.status in [200, 401]  # 401 is OK for protected endpoints
                    results.append(HealthCheckResult(
                        service="api_endpoint",
                        endpoint=url,
                        healthy=healthy,
                        response_time_ms=response_time,
                        status_code=response.status,
                        details={"endpoint": endpoint}
                    ))
            
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                results.append(HealthCheckResult(
                    service="api_endpoint",
                    endpoint=url,
                    healthy=False,
                    response_time_ms=response_time,
                    error_message=str(e),
                    details={"endpoint": endpoint}
                ))
        
        return results
    
    async def _check_authentication_flow(self) -> HealthCheckResult:
        """Check authentication flow"""
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/api/v1/users/profile"
        start_time = time.time()
        
        try:
            # Test without auth - should return 401
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                healthy = response.status == 401
                return HealthCheckResult(
                    service="authentication",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status,
                    details={"test": "unauthorized_access"},
                    error_message=None if healthy else "Auth check failed"
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="authentication",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity through API"""
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/api/v1/tokens?limit=1"
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                healthy = response.status == 200
                details = {}
                
                if healthy:
                    try:
                        data = await response.json()
                        details = {"response_type": type(data).__name__}
                    except:
                        pass
                
                return HealthCheckResult(
                    service="database",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status,
                    details=details
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="database",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity through API"""
        # Test Redis through rate limiting endpoint
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/health"
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    redis_healthy = data.get('redis', {}).get('status') == 'healthy'
                    
                    return HealthCheckResult(
                        service="redis",
                        endpoint=endpoint,
                        healthy=redis_healthy,
                        response_time_ms=response_time,
                        status_code=response.status,
                        details=data.get('redis', {})
                    )
                else:
                    return HealthCheckResult(
                        service="redis",
                        endpoint=endpoint,
                        healthy=False,
                        response_time_ms=response_time,
                        status_code=response.status,
                        error_message="Health endpoint failed"
                    )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="redis",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_solana_connectivity(self) -> HealthCheckResult:
        """Check Solana RPC connectivity"""
        # Test through our API that connects to Solana
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/health"
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    solana_healthy = data.get('solana', {}).get('status') == 'healthy'
                    
                    return HealthCheckResult(
                        service="solana_rpc",
                        endpoint=endpoint,
                        healthy=solana_healthy,
                        response_time_ms=response_time,
                        status_code=response.status,
                        details=data.get('solana', {})
                    )
                else:
                    return HealthCheckResult(
                        service="solana_rpc",
                        endpoint=endpoint,
                        healthy=False,
                        response_time_ms=response_time,
                        status_code=response.status
                    )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="solana_rpc",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_external_services(self) -> List[HealthCheckResult]:
        """Check external service dependencies"""
        external_services = [
            ("solana_mainnet", "https://api.mainnet-beta.solana.com"),
            ("solana_devnet", "https://api.devnet.solana.com"),
        ]
        
        results = []
        for service_name, url in external_services:
            start_time = time.time()
            
            try:
                # Simple health check for external services
                async with self.session.post(
                    url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    healthy = response.status == 200
                    results.append(HealthCheckResult(
                        service=service_name,
                        endpoint=url,
                        healthy=healthy,
                        response_time_ms=response_time,
                        status_code=response.status
                    ))
            
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                results.append(HealthCheckResult(
                    service=service_name,
                    endpoint=url,
                    healthy=False,
                    response_time_ms=response_time,
                    error_message=str(e)
                ))
        
        return results
    
    async def _check_response_times(self) -> HealthCheckResult:
        """Check API response times"""
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/api/v1/tokens?limit=10"
        
        # Measure multiple requests to get average
        response_times = []
        for _ in range(3):
            start_time = time.time()
            
            try:
                async with self.session.get(endpoint) as response:
                    response_time = (time.time() - start_time) * 1000
                    response_times.append(response_time)
                    
                    if response.status != 200:
                        break
            
            except Exception:
                break
            
            await asyncio.sleep(0.1)  # Small delay between requests
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            healthy = avg_response_time < 2000  # 2 second threshold
            
            return HealthCheckResult(
                service="performance",
                endpoint=endpoint,
                healthy=healthy,
                response_time_ms=avg_response_time,
                details={
                    "avg_response_time_ms": avg_response_time,
                    "measurements": len(response_times),
                    "threshold_ms": 2000
                }
            )
        else:
            return HealthCheckResult(
                service="performance",
                endpoint=endpoint,
                healthy=False,
                error_message="No successful response time measurements"
            )
    
    async def _check_resource_usage(self) -> HealthCheckResult:
        """Check system resource usage through health endpoint"""
        base_url = self.endpoints['backend_api']
        endpoint = f"{base_url}/health"
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    system_info = data.get('system', {})
                    
                    # Check if resource usage is within acceptable limits
                    cpu_usage = system_info.get('cpu_percent', 0)
                    memory_usage = system_info.get('memory_percent', 0)
                    
                    healthy = cpu_usage < 80 and memory_usage < 80
                    
                    return HealthCheckResult(
                        service="resources",
                        endpoint=endpoint,
                        healthy=healthy,
                        response_time_ms=response_time,
                        status_code=response.status,
                        details={
                            "cpu_percent": cpu_usage,
                            "memory_percent": memory_usage,
                            "thresholds": {"cpu": 80, "memory": 80}
                        }
                    )
                else:
                    return HealthCheckResult(
                        service="resources",
                        endpoint=endpoint,
                        healthy=False,
                        response_time_ms=response_time,
                        status_code=response.status
                    )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="resources",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_security_headers(self) -> HealthCheckResult:
        """Check security headers implementation"""
        endpoint = self.endpoints['frontend']
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                headers = response.headers
                
                required_headers = [
                    'X-Content-Type-Options',
                    'X-Frame-Options',
                    'X-XSS-Protection'
                ]
                
                present_headers = [h for h in required_headers if h in headers]
                healthy = len(present_headers) >= len(required_headers) * 0.8  # 80% threshold
                
                return HealthCheckResult(
                    service="security_headers",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status,
                    details={
                        "required_headers": required_headers,
                        "present_headers": present_headers,
                        "coverage_percent": (len(present_headers) / len(required_headers)) * 100
                    }
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="security_headers",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    async def _check_ssl_certificates(self) -> HealthCheckResult:
        """Check SSL certificate validity"""
        if not self.endpoints['backend_api'].startswith('https://'):
            return HealthCheckResult(
                service="ssl_certificate",
                endpoint=self.endpoints['backend_api'],
                healthy=True,  # OK for non-HTTPS environments
                details={"note": "Non-HTTPS environment"}
            )
        
        endpoint = self.endpoints['backend_api']
        start_time = time.time()
        
        try:
            # The SSL check is implicit in the HTTPS request
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                # If we get here, SSL is working
                return HealthCheckResult(
                    service="ssl_certificate",
                    endpoint=endpoint,
                    healthy=True,
                    response_time_ms=response_time,
                    status_code=response.status,
                    details={"ssl_valid": True}
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            ssl_related = any(term in str(e).lower() for term in ['ssl', 'certificate', 'tls'])
            
            return HealthCheckResult(
                service="ssl_certificate",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e),
                details={"ssl_error": ssl_related}
            )
    
    async def _check_monitoring_systems(self) -> HealthCheckResult:
        """Check monitoring systems availability"""
        if 'monitoring' not in self.endpoints:
            return HealthCheckResult(
                service="monitoring",
                endpoint="N/A",
                healthy=True,
                details={"note": "Monitoring not configured"}
            )
        
        endpoint = self.endpoints['monitoring']
        start_time = time.time()
        
        try:
            async with self.session.get(endpoint) as response:
                response_time = (time.time() - start_time) * 1000
                
                healthy = response.status == 200
                return HealthCheckResult(
                    service="monitoring",
                    endpoint=endpoint,
                    healthy=healthy,
                    response_time_ms=response_time,
                    status_code=response.status
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="monitoring",
                endpoint=endpoint,
                healthy=False,
                response_time_ms=response_time,
                error_message=str(e)
            )
    
    def generate_report(self, system_health: SystemHealth, format: str = 'json') -> str:
        """Generate health check report"""
        if format == 'json':
            return self._generate_json_report(system_health)
        elif format == 'html':
            return self._generate_html_report(system_health)
        elif format == 'text':
            return self._generate_text_report(system_health)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_json_report(self, system_health: SystemHealth) -> str:
        """Generate JSON report"""
        report = {
            'environment': system_health.environment,
            'timestamp': system_health.timestamp.isoformat(),
            'overall_healthy': system_health.overall_healthy,
            'summary': {
                'total_checks': system_health.total_checks,
                'passed_checks': system_health.passed_checks,
                'failed_checks': system_health.failed_checks,
                'success_rate': (system_health.passed_checks / system_health.total_checks * 100) if system_health.total_checks > 0 else 0,
                'check_duration_ms': system_health.check_duration_ms
            },
            'results': []
        }
        
        for result in system_health.results:
            report['results'].append({
                'service': result.service,
                'endpoint': result.endpoint,
                'healthy': result.healthy,
                'response_time_ms': result.response_time_ms,
                'status_code': result.status_code,
                'error_message': result.error_message,
                'details': result.details,
                'timestamp': result.timestamp.isoformat()
            })
        
        return json.dumps(report, indent=2)
    
    def _generate_text_report(self, system_health: SystemHealth) -> str:
        """Generate text report"""
        report = f"""
🏥 Health Check Report - {system_health.environment}
{'='*50}

Overall Status: {'✅ HEALTHY' if system_health.overall_healthy else '❌ UNHEALTHY'}
Timestamp: {system_health.timestamp.isoformat()}
Duration: {system_health.check_duration_ms:.2f}ms

Summary:
  Total Checks: {system_health.total_checks}
  Passed: {system_health.passed_checks}
  Failed: {system_health.failed_checks}
  Success Rate: {(system_health.passed_checks / system_health.total_checks * 100):.1f}%

Service Details:
"""
        
        for result in system_health.results:
            status = '✅' if result.healthy else '❌'
            report += f"  {status} {result.service}: "
            
            if result.healthy:
                report += f"{result.response_time_ms:.2f}ms"
            else:
                report += f"FAILED - {result.error_message or 'Unknown error'}"
            
            report += f" ({result.endpoint})\n"
        
        return report
    
    def _generate_html_report(self, system_health: SystemHealth) -> str:
        """Generate HTML report"""
        status_color = 'green' if system_health.overall_healthy else 'red'
        success_rate = (system_health.passed_checks / system_health.total_checks * 100) if system_health.total_checks > 0 else 0
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Health Check Report - {system_health.environment}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .status {{ font-size: 24px; color: {status_color}; font-weight: bold; }}
        .summary {{ margin: 20px 0; }}
        .service {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
        .healthy {{ border-left: 4px solid green; }}
        .unhealthy {{ border-left: 4px solid red; }}
        .details {{ font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Health Check Report</h1>
        <p><strong>Environment:</strong> {system_health.environment}</p>
        <p><strong>Timestamp:</strong> {system_health.timestamp.isoformat()}</p>
        <p><strong>Status:</strong> <span class="status">{'HEALTHY' if system_health.overall_healthy else 'UNHEALTHY'}</span></p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Checks: {system_health.total_checks}</p>
        <p>Passed: {system_health.passed_checks}</p>
        <p>Failed: {system_health.failed_checks}</p>
        <p>Success Rate: {success_rate:.1f}%</p>
        <p>Duration: {system_health.check_duration_ms:.2f}ms</p>
    </div>
    
    <h2>Service Details</h2>
"""
        
        for result in system_health.results:
            status_class = 'healthy' if result.healthy else 'unhealthy'
            status_icon = '✅' if result.healthy else '❌'
            
            html += f"""
    <div class="service {status_class}">
        <h3>{status_icon} {result.service}</h3>
        <p><strong>Endpoint:</strong> {result.endpoint}</p>
        <p><strong>Response Time:</strong> {result.response_time_ms:.2f}ms</p>
"""
            
            if result.status_code:
                html += f"<p><strong>Status Code:</strong> {result.status_code}</p>"
            
            if result.error_message:
                html += f"<p><strong>Error:</strong> {result.error_message}</p>"
            
            if result.details:
                html += f'<div class="details"><strong>Details:</strong> {json.dumps(result.details, indent=2)}</div>'
            
            html += "</div>"
        
        html += """
</body>
</html>
"""
        
        return html


async def main():
    """Main function for health checking"""
    parser = argparse.ArgumentParser(description='Anonymeme Platform Health Checker')
    parser.add_argument('--environment', required=True, choices=['development', 'staging', 'production'])
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--format', choices=['json', 'html', 'text'], default='text', help='Output format')
    parser.add_argument('--output', help='Output file (default: stdout)')
    parser.add_argument('--fail-on-unhealthy', action='store_true', help='Exit with error code if unhealthy')
    
    args = parser.parse_args()
    
    async with HealthChecker(args.environment, args.timeout) as checker:
        system_health = await checker.check_system_health()
        report = checker.generate_report(system_health, args.format)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Health check report saved to {args.output}")
        else:
            print(report)
        
        # Exit with appropriate code
        if args.fail_on_unhealthy and not system_health.overall_healthy:
            print(f"\n❌ Health check failed: {system_health.failed_checks} failures")
            sys.exit(1)
        else:
            print(f"\n✅ Health check completed: {system_health.passed_checks}/{system_health.total_checks} passed")
            sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())