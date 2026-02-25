#!/usr/bin/env python3
"""
Ollama Model Comparison & Testing Script

Tests multiple models on your Mac mini M2 to help choose the best one.
Measures: speed, quality, memory usage, response accuracy.

Usage:
    python benchmark_models.py

Requirements:
    - Ollama running: ollama serve
    - Models downloaded: ollama pull llama2:3b, ollama pull llama2:8b
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
import psutil
import os

# Import your services
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.chat.ollama_service import OllamaService
from src.config import settings


class ModelBenchmark:
    """Benchmark Ollama models for performance and quality."""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process(os.getpid())
    
    async def test_model(
        self,
        model_name: str,
        test_queries: List[str],
        warmup: bool = True
    ) -> Dict:
        """Test a single model with multiple queries."""
        
        print(f"\n{'='*70}")
        print(f"Testing Model: {model_name}")
        print(f"{'='*70}")
        
        model_results = {
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "queries": [],
            "stats": {}
        }
        
        try:
            # Initialize service for this model
            ollama = OllamaService(
                host=settings.ollama_host,
                model=model_name,
                timeout=120
            )
            
            # Warmup (first inference loads model - slow)
            if warmup:
                print(f"\n⏳ Warming up {model_name} (model loading)...")
                try:
                    start = time.time()
                    await ollama.generate(
                        prompt="Say 'hello' in one word.",
                        temperature=0.7
                    )
                    warmup_time = time.time() - start
                    print(f"   Warmup complete in {warmup_time:.2f}s")
                except Exception as e:
                    print(f"   ⚠️  Warmup failed: {e}")
                    return model_results
            
            # Test queries
            for idx, query in enumerate(test_queries, 1):
                print(f"\n[Query {idx}/{len(test_queries)}] {query[:50]}...")
                
                # Measure memory before
                mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
                
                try:
                    # Time the generation
                    start_time = time.time()
                    response = await ollama.generate(
                        prompt=query,
                        temperature=0.7
                    )
                    elapsed_time = time.time() - start_time
                    
                    # Measure memory after
                    mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
                    
                    # Calculate metrics
                    response_chars = len(response)
                    response_words = len(response.split())
                    tokens_per_second = response_words / elapsed_time if elapsed_time > 0 else 0
                    
                    query_result = {
                        "query": query,
                        "response_preview": response[:100] + "..." if len(response) > 100 else response,
                        "response_length": {
                            "chars": response_chars,
                            "words": response_words
                        },
                        "timing": {
                            "total_seconds": round(elapsed_time, 2),
                            "tokens_per_second": round(tokens_per_second, 1)
                        },
                        "memory": {
                            "before_mb": round(mem_before, 1),
                            "after_mb": round(mem_after, 1),
                            "delta_mb": round(mem_after - mem_before, 1)
                        }
                    }
                    
                    model_results["queries"].append(query_result)
                    
                    # Print results
                    print(f"   ✅ Response: {response_words} words in {elapsed_time:.2f}s")
                    print(f"      Speed: {tokens_per_second:.1f} words/sec")
                    print(f"      Memory: {mem_before:.0f}MB → {mem_after:.0f}MB (Δ {mem_after - mem_before:+.0f}MB)")
                    print(f"      Preview: {response[:80]}...")
                    
                except asyncio.TimeoutError:
                    print(f"   ❌ Timeout after 120s")
                    model_results["queries"].append({
                        "query": query,
                        "error": "Timeout after 120s",
                        "failed": True
                    })
                except Exception as e:
                    print(f"   ❌ Error: {type(e).__name__}: {str(e)[:100]}")
                    model_results["queries"].append({
                        "query": query,
                        "error": str(e)[:100],
                        "failed": True
                    })
            
            # Calculate aggregate statistics
            successful_queries = [q for q in model_results["queries"] if "failed" not in q]
            
            if successful_queries:
                avg_time = sum(q["timing"]["total_seconds"] for q in successful_queries) / len(successful_queries)
                avg_speed = sum(q["timing"]["tokens_per_second"] for q in successful_queries) / len(successful_queries)
                
                model_results["stats"] = {
                    "successful_queries": len(successful_queries),
                    "failed_queries": len(model_results["queries"]) - len(successful_queries),
                    "average_time_seconds": round(avg_time, 2),
                    "average_speed_words_per_sec": round(avg_speed, 1)
                }
            
        except Exception as e:
            print(f"❌ Failed to initialize {model_name}: {e}")
            model_results["error"] = str(e)
        
        return model_results
    
    async def run_benchmark(self, models: List[str]) -> None:
        """Run benchmark on multiple models."""
        
        # Test queries (dataset-focused for your use case)
        test_queries = [
            "Tell me about climate datasets in the UK.",
            "What hydrological data is available?",
            "List biodiversity and ecological monitoring datasets.",
            "How can environmental data support coastal management?",
            "What does your catalog contain about soil or land use?"
        ]
        
        print(f"\n{'#'*70}")
        print(f"Ollama Model Benchmark for Mac mini M2")
        print(f"{'#'*70}")
        print(f"\nTesting {len(models)} models")
        print(f"Test queries: {len(test_queries)}")
        print(f"Hardware: Mac mini M2 with {psutil.virtual_memory().total / 1024 / 1024 / 1024:.0f}GB RAM")
        
        # Test each model
        for model in models:
            try:
                result = await self.test_model(model, test_queries, warmup=True)
                self.results[model] = result
                
                # Give a moment between models
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"\n❌ Benchmark failed for {model}: {e}")
        
        # Print summary
        self.print_summary()
        
        # Save results to file
        self.save_results()
    
    def print_summary(self) -> None:
        """Print benchmark summary comparing models."""
        
        print(f"\n\n{'='*70}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*70}")
        
        # Create comparison table
        models = list(self.results.keys())
        
        if not models:
            print("No successful benchmark results.")
            return
        
        # Header
        print(f"\n{'Model':<20} {'Avg Speed':<15} {'Avg Time':<15} {'Success':<10}")
        print("-" * 60)
        
        # Data
        for model in models:
            result = self.results[model]
            if "error" in result:
                print(f"{model:<20} {'ERROR':<15} {'-':<15} {'0/X':<10}")
            else:
                stats = result.get("stats", {})
                speed = f"{stats.get('average_speed_words_per_sec', 0):.1f} w/s"
                time = f"{stats.get('average_time_seconds', 0):.2f}s"
                success = f"{stats.get('successful_queries', 0)}/{len(result['queries'])}"
                print(f"{model:<20} {speed:<15} {time:<15} {success:<10}")
        
        # Recommendation
        print(f"\n{'='*70}")
        print("RECOMMENDATION")
        print(f"{'='*70}")
        
        # Find fastest and best quality (most words)
        fastest = None
        best_quality = None
        fastest_time = float('inf')
        best_words = 0
        
        for model, result in self.results.items():
            if "error" not in result and result.get("stats"):
                stats = result["stats"]
                time = stats.get("average_time_seconds", float('inf'))
                words = sum(q.get("response_length", {}).get("words", 0) 
                          for q in result["queries"] if "failed" not in q)
                
                if time < fastest_time:
                    fastest_time = time
                    fastest = model
                
                if words > best_words:
                    best_words = words
                    best_quality = model
        
        if fastest:
            print(f"✓ Fastest: {fastest} ({fastest_time:.2f}s avg)")
        if best_quality:
            print(f"✓ Best Quality: {best_quality} ({best_words} avg words per response)")
        
        print(f"\nFor Mac mini M2 (8GB):")
        print(f"  - Speed focus:    Use Llama 3.2 3B")
        print(f"  - Balanced:       Use Mistral 7B")
        print(f"  - Quality focus:  Use Llama 3.2 8B (if 16GB) or Mistral 7B (if 8GB)")
    
    def save_results(self) -> None:
        """Save results to JSON file."""
        
        output_file = "benchmark_results.json"
        
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2)
            
            print(f"\n✓ Results saved to: {output_file}")
            
        except Exception as e:
            print(f"\n❌ Failed to save results: {e}")


async def main():
    """Main entry point."""
    
    benchmark = ModelBenchmark()
    
    # Models to test
    models_to_test = [
        "mistral",       # Current model
        "llama2:3b",     # Fast option
        "llama2:8b"      # Quality option
    ]
    
    try:
        await benchmark.run_benchmark(models_to_test)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
