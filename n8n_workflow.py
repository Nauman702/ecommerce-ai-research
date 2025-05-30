import requests
import json
import time
from datetime import datetime, timedelta
import schedule
from typing import Dict, List
from scrapers import ProductDataManager
from ai_analyzer import ProductAnalysisEngine, KeywordAnalyzer, LlamaAnalyzer
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse

class WorkflowManager:
    def __init__(self, n8n_webhook_url: str, db_config: Dict):
        self.n8n_webhook_url = n8n_webhook_url
        self.db_config = db_config
        self.product_manager = ProductDataManager()
        self.analyzer = ProductAnalysisEngine(db_config)
        self.keyword_analyzer = KeywordAnalyzer(LlamaAnalyzer())
        
    def trigger_research_workflow(self, keywords: List[str], categories: List[str] = None) -> Dict:
        """
        Main workflow to research products across all platforms
        """
        workflow_id = f"research_{int(time.time())}"
        
        workflow_result = {
            'workflow_id': workflow_id,
            'started_at': datetime.now().isoformat(),
            'keywords': keywords,
            'categories': categories or [],
            'status': 'running',
            'results': {}
        }
        
        try:
            # Step 1: Data Collection
            print(f"[{workflow_id}] Starting data collection...")
            collection_results = self.collect_product_data(keywords, categories)
            workflow_result['results']['collection'] = collection_results
            
            # Step 2: Store products in database
            print(f"[{workflow_id}] Storing products in database...")
            storage_results = self.store_products(collection_results)
            workflow_result['results']['storage'] = storage_results
            
            # Step 3: AI Analysis
            print(f"[{workflow_id}] Running AI analysis...")
            analysis_results = self.analyzer.batch_analyze_products(limit=200)
            workflow_result['results']['analysis'] = analysis_results
            
            # Step 4: Generate insights
            print(f"[{workflow_id}] Generating market insights...")
            market_report = self.analyzer.generate_market_report()
            workflow_result['results']['insights'] = market_report
            
            # Step 5: Send notifications
            print(f"[{workflow_id}] Sending notifications...")
            notification_result = self.send_workflow_notification(workflow_result)
            workflow_result['results']['notifications'] = notification_result
            
            workflow_result['status'] = 'completed'
            workflow_result['completed_at'] = datetime.now().isoformat()
            
        except Exception as e:
            workflow_result['status'] = 'failed'
            workflow_result['error'] = str(e)
            print(f"[{workflow_id}] Workflow failed: {e}")
        
        return workflow_result
    
    def collect_product_data(self, keywords: List[str], categories: List[str] = None) -> Dict:
        """Collect product data from all platforms"""
        all_results = {}
        total_products = 0
        
        for keyword in keywords:
            for category in (categories or ['']):
                try:
                    print(f"Searching for: {keyword} in {category or 'all categories'}")
                    
                    # Search across all platforms
                    platform_results = self.product_manager.search_all_platforms(
                        keywords=keyword,
                        category=category,
                        limit_per_platform=25
                    )
                    
                    # Combine results
                    for platform, products in platform_results.items():
                        if platform not in all_results:
                            all_results[platform] = []
                        all_results[platform].extend(products)
                        total_products += len(products)
                    
                    # Add delay to avoid rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error collecting data for {keyword} in {category}: {e}")
        
        return {
            'total_products_found': total_products,
            'platforms': list(all_results.keys()),
            'products_by_platform': {k: len(v) for k, v in all_results.items()},
            'products': all_results
        }
    
    def store_products(self, collection_results: Dict) -> Dict:
        """Store collected products in database"""
        stored_count = 0
        errors = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            products_data = collection_results.get('products', {})
            
            for platform, products in products_data.items():
                for product in products:
                    try:
                        # Convert product to dictionary if it's not already
                        if hasattr(product, '__dict__'):
                            product_dict = product.__dict__
                        else:
                            product_dict = product
                        
                        # Insert product
                        insert_query = """
                        INSERT INTO products 
                        (title, platform, category, price, currency, sales_count, 
                         rating, review_count, seller_info, product_url, description, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (title, platform) DO NOTHING
                        """
                        
                        cursor.execute(insert_query, (
                            product_dict.get('title', ''),
                            product_dict.get('platform', ''),
                            product_dict.get('category', ''),
                            product_dict.get('price', 0),
                            product_dict.get('currency', 'USD'),
                            product_dict.get('sales_count'),
                            product_dict.get('rating'),
                            product_dict.get('review_count'),
                            product_dict.get('seller_info'),
                            product_dict.get('product_url'),
                            product_dict.get('description'),
                            product_dict.get('tags', [])
                        ))
                        
                        stored_count += 1
                        
                    except Exception as e:
                        errors += 1
                        print(f"Error storing product: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Database error: {e}")
            errors += 1
        
        return {
            'products_stored': stored_count,
            'errors': errors,
            'success_rate': (stored_count / (stored_count + errors)) * 100 if (stored_count + errors) > 0 else 0
        }
    
    def send_workflow_notification(self, workflow_result: Dict) -> Dict:
        """Send workflow completion notification via n8n webhook"""
        try:
            # Prepare notification payload
            notification_data = {
                'workflow_id': workflow_result['workflow_id'],
                'status': workflow_result['status'],
                'summary': {
                    'total_products': workflow_result['results'].get('collection', {}).get('total_products_found', 0),
                    'high_opportunities': workflow_result['results'].get('analysis', {}).get('high_opportunity', 0),
                    'top_platform': 'N/A',
                    'completion_time': workflow_result.get('completed_at', 'N/A')
                },
                'top_opportunities': []
            }
            
            # Add top opportunities if available
            insights = workflow_result['results'].get('insights', {})
            if 'top_opportunities' in insights:
                notification_data['top_opportunities'] = insights['top_opportunities'][:5]
            
            # Send to n8n webhook
            response = requests.post(
                self.n8n_webhook_url,
                json=notification_data,
                timeout=30
            )
            
            return {
                'notification_sent': response.status_code == 200,
                'response_code': response.status_code,
                'webhook_url': self.n8n_webhook_url
            }
            
        except Exception as e:
            return {
                'notification_sent': False,
                'error': str(e)
            }
    
    def schedule_automated_research(self):
        """Set up automated research schedules"""
        
        # Daily trend research
        schedule.every().day.at("09:00").do(
            self.run_daily_trend_research
        )
        
        # Weekly comprehensive research
        schedule.every().monday.at("10:00").do(
            self.run_weekly_comprehensive_research
        )
        
        # Hourly opportunity monitoring
        schedule.every().hour.do(
            self.run_opportunity_monitoring
        )
        
        print("Automated research schedules set up:")
        print("- Daily trend research: 09:00")
        print("- Weekly comprehensive research: Monday 10:00")
        print("- Hourly opportunity monitoring")
        
        # Run the scheduler continuously
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def run_daily_trend_research(self):
        """Run daily automated trend research"""
        trending_keywords = [
            "trending", "viral", "popular", "bestseller", "hot item"
        ]
        
        print("Starting daily trend research...")
        result = self.trigger_research_workflow(
            keywords=trending_keywords,
            categories=["Electronics", "Fashion", "Home & Garden", "Sports"]
        )
        
        print(f"Daily trend research completed: {result['workflow_id']}")
        return result
    
    def run_weekly_comprehensive_research(self):
        """Run weekly comprehensive market research"""
        comprehensive_keywords = [
            "new products", "innovative", "gadgets", "accessories", 
            "tools", "beauty", "fitness", "tech", "kitchen", "outdoor"
        ]
        
        print("Starting weekly comprehensive research...")
        result = self.trigger_research_workflow(
            keywords=comprehensive_keywords,
            categories=["Electronics", "Fashion", "Home & Garden", "Sports", "Beauty", "Automotive"]
        )
        
        print(f"Weekly comprehensive research completed: {result['workflow_id']}")
        return result
    
    def run_opportunity_monitoring(self):
        """Monitor for new high-opportunity products"""
        try:
            # Check for products added in the last hour with high opportunity scores
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT p.title, p.platform, pm.opportunity_score, pm.ai_recommendation
            FROM products p
            JOIN product_metrics pm ON p.id = pm.product_id
            WHERE p.created_at >= NOW() - INTERVAL '1 hour'
            AND pm.opportunity_score >= 8.0
            ORDER BY pm.opportunity_score DESC
            LIMIT 10
            """
            
            cursor.execute(query)
            high_opportunities = [dict(row) for row in cursor.fetchall()]
            
            if high_opportunities:
                # Send immediate notification for high-opportunity products
                notification_data = {
                    'alert_type': 'high_opportunity',
                    'timestamp': datetime.now().isoformat(),
                    'opportunities_found': len(high_opportunities),
                    'products': high_opportunities
                }
                
                requests.post(
                    self.n8n_webhook_url.replace('/research', '/alerts'),
                    json=notification_data,
                    timeout=10
                )
                
                print(f"High opportunity alert sent: {len(high_opportunities)} products")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"Error in opportunity monitoring: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to manage database size"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Delete old products and their metrics
            cleanup_query = """
            DELETE FROM products 
            WHERE created_at < NOW() - INTERVAL '%s days'
            AND id NOT IN (
                SELECT DISTINCT product_id 
                FROM product_metrics 
                WHERE opportunity_score >= 7.0
            )
            """
            
            cursor.execute(cleanup_query, (days_to_keep,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"Cleaned up {deleted_count} old products")
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return 0

def main():
    parser = argparse.ArgumentParser(description="Ecommerce Product Research Workflow")
    parser.add_argument('--keywords', type=str, help="Comma-separated list of keywords to research")
    parser.add_argument('--categories', type=str, help="Comma-separated list of categories to research")
    parser.add_argument('--webhook', type=str, default="http://localhost:5678/webhook/research", help="n8n webhook URL")
    parser.add_argument('--daemon', action='store_true', help="Run in daemon mode for scheduled tasks")
    
    args = parser.parse_args()
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ecommerce_research',
        'user': 'researcher',
        'password': 'research123'
    }
    
    # Initialize workflow manager
    manager = WorkflowManager(args.webhook, db_config)
    
    if args.daemon:
        print("Starting in daemon mode with scheduled tasks...")
        manager.schedule_automated_research()
    else:
        # Run one-time research
        keywords = args.keywords.split(',') if args.keywords else ['trending products']
        categories = args.categories.split(',') if args.categories else []
        
        print(f"Starting research for keywords: {keywords}")
        if categories:
            print(f"With categories: {categories}")
        
        result = manager.trigger_research_workflow(keywords, categories)
        print(f"Research completed with status: {result['status']}")

if __name__ == "__main__":
    main()