#!/usr/bin/env python3
"""
Performance benchmark script for serverless chat backend
Analyzes Big O complexity and performance characteristics
"""

import json
import time
import statistics
import concurrent.futures
import requests
import argparse
import sys
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np

class PerformanceBenchmarker:
    """
    Comprehensive performance testing suite
    """
    
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
        self.results = {}
    
    def measure_latency(self, message: str, num_requests: int = 100) -> Dict[str, float]:
        """
        Measure API latency statistics
        Time Complexity: O(n) where n = num_requests
        """
        latencies = []
        
        for _ in range(num_requests):
            start_time = time.time()
            try:
                response = requests.post(
                    self.api_endpoint,
                    json={"message": message},
                    timeout=30
                )
                latency = time.time() - start_time
                if response.status_code == 200:
                    latencies.append(latency * 1000)  # Convert to milliseconds
            except Exception as e:
                print(f"Request failed: {e}")
        
        if not latencies:
            return {"error": "No successful requests"}
        
        return {
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": np.percentile(latencies, 95),
            "p99_ms": np.percentile(latencies, 99),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "std_dev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "successful_requests": len(latencies),
            "total_requests": num_requests
        }
    
    def test_input_size_complexity(self) -> Dict[str, List]:
        """
        Test how performance scales with input size
        Validates O(n) complexity for input processing
        """
        input_sizes = [10, 50, 100, 200, 500, 1000, 1500]
        latencies = []
        
        for size in input_sizes:
            message = "a" * size  # Create message of specified length
            result = self.measure_latency(message, num_requests=10)
            if "mean_ms" in result:
                latencies.append(result["mean_ms"])
            else:
                latencies.append(None)
            
            print(f"Input size {size}: {result.get('mean_ms', 'Failed'):.2f}ms")
        
        return {
            "input_sizes": input_sizes,
            "latencies": latencies
        }
    
    def test_concurrent_load(self, max_concurrent: int = 50) -> Dict[str, any]:
        """
        Test system behavior under concurrent load
        Measures throughput and error rates
        """
        concurrency_levels = [1, 5, 10, 20, 30, 40, 50]
        results = []
        
        for concurrent in concurrency_levels:
            if concurrent > max_concurrent:
                break
                
            print(f"Testing {concurrent} concurrent requests...")
            
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            
            def make_request():
                try:
                    response = requests.post(
                        self.api_endpoint,
                        json={"message": f"Load test with {concurrent} concurrent users"},
                        timeout=30
                    )
                    return response.status_code == 200
                except:
                    return False
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrent)]
                
                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        successful_requests += 1
                    else:
                        failed_requests += 1
            
            total_time = time.time() - start_time
            throughput = successful_requests / total_time if total_time > 0 else 0
            
            results.append({
                "concurrency": concurrent,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "total_time": total_time,
                "throughput_rps": throughput,
                "error_rate": failed_requests / (successful_requests + failed_requests) if (successful_requests + failed_requests) > 0 else 1
            })
        
        return {"concurrency_results": results}
    
    def test_rate_limiting(self) -> Dict[str, any]:
        """
        Test rate limiting behavior
        Expected: O(1) rate limit checking
        """
        print("Testing rate limiting...")
        
        # Send requests rapidly to trigger rate limiting
        responses = []
        start_time = time.time()
        
        for i in range(20):
            try:
                response = requests.post(
                    self.api_endpoint,
                    json={"message": f"Rate limit test {i}"},
                    timeout=10
                )
                responses.append({
                    "status_code": response.status_code,
                    "time": time.time() - start_time
                })
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                responses.append({
                    "status_code": "error",
                    "time": time.time() - start_time,
                    "error": str(e)
                })
        
        rate_limited_count = sum(1 for r in responses if r.get("status_code") == 429)
        successful_count = sum(1 for r in responses if r.get("status_code") == 200)
        
        return {
            "total_requests": len(responses),
            "successful_requests": successful_count,
            "rate_limited_requests": rate_limited_count,
            "rate_limit_percentage": (rate_limited_count / len(responses)) * 100,
            "responses": responses
        }
    
    def generate_performance_report(self) -> Dict[str, any]:
        """
        Generate comprehensive performance report
        """
        print("=== Performance Benchmark Report ===\n")
        
        # Basic latency test
        print("1. Latency Analysis...")
        latency_results = self.measure_latency("Hello, this is a performance test!", 50)
        self.results["latency"] = latency_results
        
        # Input size complexity test
        print("\n2. Input Size Complexity Analysis...")
        complexity_results = self.test_input_size_complexity()
        self.results["input_complexity"] = complexity_results
        
        # Concurrent load test
        print("\n3. Concurrent Load Testing...")
        load_results = self.test_concurrent_load(20)
        self.results["load_testing"] = load_results
        
        # Rate limiting test
        print("\n4. Rate Limiting Analysis...")
        rate_limit_results = self.test_rate_limiting()
        self.results["rate_limiting"] = rate_limit_results
        
        return self.results
    
    def save_results(self, filename: str = "benchmark-results.json"):
        """Save benchmark results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults saved to {filename}")
    
    def plot_performance_charts(self):
        """Generate performance visualization charts"""
        try:
            # Input size vs latency plot
            if "input_complexity" in self.results:
                plt.figure(figsize=(12, 8))
                
                plt.subplot(2, 2, 1)
                data = self.results["input_complexity"]
                valid_data = [(size, lat) for size, lat in zip(data["input_sizes"], data["latencies"]) if lat is not None]
                
                if valid_data:
                    sizes, lats = zip(*valid_data)
                    plt.plot(sizes, lats, 'bo-')
                    plt.xlabel('Input Size (characters)')
                    plt.ylabel('Latency (ms)')
                    plt.title('Input Size vs Latency (O(n) complexity)')
                    plt.grid(True)
                
                # Concurrent load plot
                if "load_testing" in self.results:
                    plt.subplot(2, 2, 2)
                    load_data = self.results["load_testing"]["concurrency_results"]
                    concurrency = [r["concurrency"] for r in load_data]
                    throughput = [r["throughput_rps"] for r in load_data]
                    
                    plt.plot(concurrency, throughput, 'ro-')
                    plt.xlabel('Concurrent Users')
                    plt.ylabel('Throughput (RPS)')
                    plt.title('Concurrency vs Throughput')
                    plt.grid(True)
                
                # Error rate plot
                plt.subplot(2, 2, 3)
                error_rates = [r["error_rate"] * 100 for r in load_data]
                plt.plot(concurrency, error_rates, 'go-')
                plt.xlabel('Concurrent Users')
                plt.ylabel('Error Rate (%)')
                plt.title('Concurrency vs Error Rate')
                plt.grid(True)
                
                # Latency distribution
                if "latency" in self.results:
                    plt.subplot(2, 2, 4)
                    latency_data = self.results["latency"]
                    metrics = ['mean_ms', 'median_ms', 'p95_ms', 'p99_ms']
                    values = [latency_data.get(m, 0) for m in metrics]
                    
                    plt.bar(metrics, values)
                    plt.ylabel('Latency (ms)')
                    plt.title('Latency Distribution')
                    plt.xticks(rotation=45)
                
                plt.tight_layout()
                plt.savefig('performance_charts.png', dpi=300, bbox_inches='tight')
                print("Performance charts saved to performance_charts.png")
                
        except ImportError:
            print("Matplotlib not available, skipping chart generation")
        except Exception as e:
            print(f"Error generating charts: {e}")

def main():
    parser = argparse.ArgumentParser(description='Performance benchmark for serverless chat API')
    parser.add_argument('--endpoint', required=True, help='API Gateway endpoint URL')
    parser.add_argument('--output', default='benchmark-results.json', help='Output file for results')
    parser.add_argument('--charts', action='store_true', help='Generate performance charts')
    
    args = parser.parse_args()
    
    print(f"Starting performance benchmark for: {args.endpoint}")
    print("=" * 60)
    
    benchmarker = PerformanceBenchmarker(args.endpoint)
    results = benchmarker.generate_performance_report()
    
    # Print summary
    print("\n=== PERFORMANCE SUMMARY ===")
    if "latency" in results:
        lat = results["latency"]
        print(f"Average Latency: {lat.get('mean_ms', 0):.2f}ms")
        print(f"95th Percentile: {lat.get('p95_ms', 0):.2f}ms")
        print(f"Success Rate: {lat.get('successful_requests', 0)}/{lat.get('total_requests', 0)}")
    
    if "load_testing" in results and results["load_testing"]["concurrency_results"]:
        max_throughput = max(r["throughput_rps"] for r in results["load_testing"]["concurrency_results"])
        print(f"Peak Throughput: {max_throughput:.2f} RPS")
    
    if "rate_limiting" in results:
        rl = results["rate_limiting"]
        print(f"Rate Limiting: {rl.get('rate_limit_percentage', 0):.1f}% of requests rate limited")
    
    benchmarker.save_results(args.output)
    
    if args.charts:
        benchmarker.plot_performance_charts()
    
    print("\nBenchmark completed successfully!")

if __name__ == "__main__":
    main()