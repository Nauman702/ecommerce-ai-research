import json
import requests
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import asdict
import re
import sqlite3
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

class LlamaAnalyzer:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3"
    
    def query_llama(self, prompt: str, system_prompt: str = "") -> str:
        """Send query to local Llama model via Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: {response.status_code}"
                
        except Exception as e:
            return f"Connection error: {str(e)}"

class ProductAnalysisEngine:
    def __init__(self, db_config: Dict):
        self.llama = LlamaAnalyzer()
        self.db_config = db_config
        self.connect_db()
    
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"Database connection error: {e}")
    
    def analyze_product_opportunity(self, product: Dict) -> Dict:
        """
        Comprehensive analysis of a product's market opportunity
        """
        analysis_result = {
            'trend_score': 0.0,
            'competition_level': 'Unknown',
            'profit_potential': 0.0,
            'market_demand': 0.0,
            'keyword_difficulty': 0.0,
            'opportunity_score': 0.0,
            'ai_recommendation': '',
            'risk_factors': [],
            'success_indicators': []
        }
        
        try:
            # 1. Analyze product title and description for trends
            trend_analysis = self.analyze_market_trends(product)
            analysis_result['trend_score'] = trend_analysis['score']
            
            # 2. Assess competition level
            competition_analysis = self.analyze_competition(product)
            analysis_result['competition_level'] = competition_analysis['level']
            
            # 3. Calculate profit potential
            profit_analysis = self.calculate_profit_potential(product)
            analysis_result['profit_potential'] = profit_analysis['score']
            
            # 4. Assess market demand
            demand_analysis = self.assess_market_demand(product)
            analysis_result['market_demand'] = demand_analysis['score']
            
            # 5. Get AI recommendation
            ai_recommendation = self.get_ai_recommendation(product, analysis_result)
            analysis_result['ai_recommendation'] = ai_recommendation
            
            # 6. Calculate overall opportunity score
            analysis_result['opportunity_score'] = self.calculate_opportunity_score(analysis_result)
            
        except Exception as e:
            print(f"Error analyzing product: {e}")
        
        return analysis_result
    
    def analyze_market_trends(self, product: Dict) -> Dict:
        """Analyze current market trends for the product"""
        system_prompt = """You are a market trend analyst. Analyze the product and determine if it's trending upward, stable, or declining. Consider factors like:
        - Product category trends
        - Seasonal patterns
        - Technology adoption
        - Consumer behavior shifts
        
        Return your analysis as a trend score from 1-10 where 10 is highly trending."""
        
        prompt = f"""
        Analyze this product for market trends:
        Title: {product.get('title', 'N/A')}
        Category: {product.get('category', 'N/A')}
        Platform: {product.get('platform', 'N/A')}
        Price: ${product.get('price', 0)}
        
        Provide a trend score (1-10) and brief explanation.
        """
        
        ai_response = self.llama.query_llama(prompt, system_prompt)
        
        # Extract trend score from AI response
        trend_score = self.extract_numeric_score(ai_response, default=5.0)
        
        return {
            'score': min(10.0, max(1.0, trend_score)),
            'explanation': ai_response
        }
    
    def analyze_competition(self, product: Dict) -> Dict:
        """Analyze competition level for the product"""
        # Query database for similar products
        similar_products = self.find_similar_products(product)
        
        competition_count = len(similar_products)
        
        # Determine competition level
        if competition_count < 10:
            level = "Low"
            score = 8.0
        elif competition_count < 50:
            level = "Medium"
            score = 6.0
        elif competition_count < 200:
            level = "High"
            score = 4.0
        else:
            level = "Very High"
            score = 2.0
        
        return {
            'level': level,
            'score': score,
            'competitor_count': competition_count
        }
    
    def calculate_profit_potential(self, product: Dict) -> Dict:
        """Calculate profit potential based on price, sales data, etc."""
        price = product.get('price', 0)
        sales_count = product.get('sales_count', 0)
        platform = product.get('platform', '').lower()
        
        # Platform-specific profit margin estimates
        margin_estimates = {
            'ebay': 0.25,      # 25% after fees
            'amazon': 0.15,    # 15% after fees and competition
            'etsy': 0.35,      # 35% for handmade/unique items
            'shopify': 0.45    # 45% for direct-to-consumer
        }
        
        estimated_margin = margin_estimates.get(platform, 0.25)
        estimated_profit = price * estimated_margin
        
        # Score based on profit potential
        if estimated_profit > 50:
            score = 9.0
        elif estimated_profit > 25:
            score = 7.0
        elif estimated_profit > 10:
            score = 5.0
        elif estimated_profit > 5:
            score = 3.0
        else:
            score = 2.0
        
        # Boost score if high sales volume
        if sales_count and sales_count > 100:
            score = min(10.0, score + 1.5)
        elif sales_count and sales_count > 50:
            score = min(10.0, score + 1.0)
        
        return {
            'score': score,
            'estimated_profit': estimated_profit,
            'estimated_margin': estimated_margin
        }
    
    def assess_market_demand(self, product: Dict) -> Dict:
        """Assess market demand using various signals"""
        title = product.get('title', '')
        category = product.get('category', '')
        sales_count = product.get('sales_count', 0)
        review_count = product.get('review_count', 0)
        
        system_prompt = """You are a market demand analyst. Assess the market demand for this product based on:
        - Product popularity indicators
        - Market size for the category
        - Consumer interest trends
        - Sales performance metrics
        
        Rate demand from 1-10 where 10 indicates very high demand."""
        
        prompt = f"""
        Assess market demand for this product:
        Title: {title}
        Category: {category}
        Sales Count: {sales_count}
        Review Count: {review_count}
        
        Consider current market trends and consumer behavior.
        Provide a demand score (1-10) and reasoning.
        """
        
        ai_response = self.llama.query_llama(prompt, system_prompt)
        demand_score = self.extract_numeric_score(ai_response, default=5.0)
        
        # Adjust based on actual sales/review data
        if sales_count > 1000:
            demand_score = min(10.0, demand_score + 1.5)
        elif sales_count > 100:
            demand_score = min(10.0, demand_score + 1.0)
        
        if review_count > 500:
            demand_score = min(10.0, demand_score + 1.0)
        
        return {
            'score': min(10.0, max(1.0, demand_score)),
            'explanation': ai_response
        }
    
    def get_ai_recommendation(self, product: Dict, analysis: Dict) -> str:
        """Get comprehensive AI recommendation for the product"""
        system_prompt = """You are an expert ecommerce consultant. Based on the product data and analysis scores, provide a comprehensive recommendation about whether this product represents a good business opportunity. Include:
        1. Overall recommendation (Highly Recommended/Recommended/Caution/Avoid)
        2. Key strengths and weaknesses
        3. Specific action items
        4. Risk mitigation strategies
        
        Keep your response concise but actionable."""
        
        prompt = f"""
        Product Analysis Summary:
        - Product: {product.get('title', 'N/A')}
        - Platform: {product.get('platform', 'N/A')}
        - Price: ${product.get('price', 0)}
        - Category: {product.get('category', 'N/A')}
        
        Analysis Scores:
        - Trend Score: {analysis.get('trend_score', 0)}/10
        - Competition Level: {analysis.get('competition_level', 'Unknown')}
        - Profit Potential: {analysis.get('profit_potential', 0)}/10
        - Market Demand: {analysis.get('market_demand', 0)}/10
        
        Provide your expert recommendation and strategy.
        """
        
        return self.llama.query_llama(prompt, system_prompt)
    
    def calculate_opportunity_score(self, analysis: Dict) -> float:
        """Calculate overall opportunity score weighted by importance"""
        weights = {
            'trend_score': 0.25,
            'profit_potential': 0.30,
            'market_demand': 0.30,
            'competition_score': 0.15  # Lower competition = higher score
        }
        
        # Convert competition level to numeric score
        competition_scores = {
            'Low': 9.0,
            'Medium': 6.0,
            'High': 4.0,
            'Very High': 2.0,
            'Unknown': 5.0
        }
        
        competition_score = competition_scores.get(analysis.get('competition_level', 'Unknown'), 5.0)
        
        opportunity_score = (
            analysis.get('trend_score', 5.0) * weights['trend_score'] +
            analysis.get('profit_potential', 5.0) * weights['profit_potential'] +
            analysis.get('market_demand', 5.0) * weights['market_demand'] +
            competition_score * weights['competition_score']
        )
        
        return round(opportunity_score, 2)
    
    def find_similar_products(self, product: Dict) -> List[Dict]:
        """Find similar products in database for competition analysis"""
        try:
            title = product.get('title', '').lower()
            category = product.get('category', '').lower()
            platform = product.get('platform', '').lower()
            
            # Extract key terms from title
            key_terms = self.extract_key_terms(title)
            
            # Build search query
            search_conditions = []
            params = []
            
            if key_terms:
                search_conditions.append("LOWER(title) SIMILAR TO %s")
                params.append(f"%{'%'.join(key_terms)}%")
            
            if category:
                search_conditions.append("LOWER(category) = %s")
                params.append(category)
            
            # Exclude same platform to focus on cross-platform competition
            if platform:
                search_conditions.append("LOWER(platform) != %s")
                params.append(platform)
            
            if search_conditions:
                query = f"""
                SELECT * FROM products 
                WHERE {' AND '.join(search_conditions)}
                LIMIT 100
                """
                
                self.cursor.execute(query, params)
                return [dict(row) for row in self.cursor.fetchall()]
            
        except Exception as e:
            print(f"Error finding similar products: {e}")
        
        return []
    
    def extract_key_terms(self, title: str) -> List[str]:
        """Extract key terms from product title for similarity matching"""
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'new', 'used'}
        
        # Clean and split title
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        key_terms = [word for word in words if word not in stop_words]
        
        # Return top 5 most relevant terms
        return key_terms[:5]
    
    def extract_numeric_score(self, text: str, default: float = 5.0) -> float:
        """Extract numeric score from AI response text"""
        # Look for patterns like "score: 7", "7/10", "rating of 8", etc.
        patterns = [
            r'score[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)[/\s]*(?:out of |/)?\s*10',
            r'rating[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)[/\s]*10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    score = float(match.group(1))
                    return min(10.0, max(1.0, score))
                except ValueError:
                    continue
        
        return default
    
    def save_analysis_results(self, product_id: int, analysis: Dict):
        """Save analysis results to database"""
        try:
            query = """
            INSERT INTO product_metrics 
            (product_id, trend_score, competition_level, profit_potential, 
             market_demand, opportunity_score, ai_recommendation)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id, date_analyzed) 
            DO UPDATE SET
                trend_score = EXCLUDED.trend_score,
                competition_level = EXCLUDED.competition_level,
                profit_potential = EXCLUDED.profit_potential,
                market_demand = EXCLUDED.market_demand,
                opportunity_score = EXCLUDED.opportunity_score,
                ai_recommendation = EXCLUDED.ai_recommendation
            """
            
            self.cursor.execute(query, (
                product_id,
                analysis.get('trend_score', 0),
                analysis.get('competition_level', 'Unknown'),
                analysis.get('profit_potential', 0),
                analysis.get('market_demand', 0),
                analysis.get('opportunity_score', 0),
                analysis.get('ai_recommendation', '')
            ))
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Error saving analysis: {e}")
            self.conn.rollback()
    
    def batch_analyze_products(self, limit: int = 100) -> Dict:
        """Analyze multiple products in batch"""
        try:
            # Get products that need analysis
            query = """
            SELECT p.* FROM products p
            LEFT JOIN product_metrics pm ON p.id = pm.product_id
            WHERE pm.id IS NULL OR pm.created_at < NOW() - INTERVAL '7 days'
            ORDER BY p.created_at DESC
            LIMIT %s
            """
            
            self.cursor.execute(query, (limit,))
            products = [dict(row) for row in self.cursor.fetchall()]
            
            analysis_results = {
                'total_analyzed': 0,
                'high_opportunity': 0,
                'medium_opportunity': 0,
                'low_opportunity': 0,
                'recommendations': []
            }
            
            for product in products:
                try:
                    print(f"Analyzing: {product['title'][:50]}...")
                    
                    analysis = self.analyze_product_opportunity(product)
                    self.save_analysis_results(product['id'], analysis)
                    
                    analysis_results['total_analyzed'] += 1
                    
                    # Categorize by opportunity score
                    score = analysis.get('opportunity_score', 0)
                    if score >= 7.5:
                        analysis_results['high_opportunity'] += 1
                        analysis_results['recommendations'].append({
                            'product': product['title'],
                            'platform': product['platform'],
                            'score': score,
                            'recommendation': analysis.get('ai_recommendation', '')
                        })
                    elif score >= 5.5:
                        analysis_results['medium_opportunity'] += 1
                    else:
                        analysis_results['low_opportunity'] += 1
                    
                except Exception as e:
                    print(f"Error analyzing product {product['id']}: {e}")
                    continue
            
            return analysis_results
            
        except Exception as e:
            print(f"Error in batch analysis: {e}")
            return {'error': str(e)}
    
    def generate_market_report(self) -> Dict:
        """Generate comprehensive market analysis report"""
        try:
            # Get top opportunities
            top_opportunities_query = """
            SELECT p.title, p.platform, p.category, p.price, pm.opportunity_score, pm.ai_recommendation
            FROM products p
            JOIN product_metrics pm ON p.id = pm.product_id
            WHERE pm.opportunity_score >= 7.0
            ORDER BY pm.opportunity_score DESC
            LIMIT 20
            """
            
            self.cursor.execute(top_opportunities_query)
            top_opportunities = [dict(row) for row in self.cursor.fetchall()]
            
            # Get platform performance
            platform_performance_query = """
            SELECT 
                p.platform,
                COUNT(*) as total_products,
                AVG(pm.opportunity_score) as avg_opportunity_score,
                COUNT(CASE WHEN pm.opportunity_score >= 7.0 THEN 1 END) as high_opportunity_count
            FROM products p
            JOIN product_metrics pm ON p.id = pm.product_id
            GROUP BY p.platform
            ORDER BY avg_opportunity_score DESC
            """
            
            self.cursor.execute(platform_performance_query)
            platform_performance = [dict(row) for row in self.cursor.fetchall()]
            
            # Get trending categories
            trending_categories_query = """
            SELECT 
                p.category,
                COUNT(*) as product_count,
                AVG(pm.trend_score) as avg_trend_score,
                AVG(pm.opportunity_score) as avg_opportunity_score
            FROM products p
            JOIN product_metrics pm ON p.id = pm.product_id
            WHERE p.category IS NOT NULL AND p.category != ''
            GROUP BY p.category
            HAVING COUNT(*) >= 3
            ORDER BY avg_trend_score DESC, avg_opportunity_score DESC
            LIMIT 15
            """
            
            self.cursor.execute(trending_categories_query)
            trending_categories = [dict(row) for row in self.cursor.fetchall()]
            
            return {
                'report_generated': datetime.now().isoformat(),
                'top_opportunities': top_opportunities,
                'platform_performance': platform_performance,
                'trending_categories': trending_categories,
                'summary': {
                    'total_high_opportunities': len(top_opportunities),
                    'best_performing_platform': platform_performance[0]['platform'] if platform_performance else 'N/A',
                    'top_trending_category': trending_categories[0]['category'] if trending_categories else 'N/A'
                }
            }
            
        except Exception as e:
            print(f"Error generating market report: {e}")
            return {'error': str(e)}
    
    def close_connection(self):
        """Close database connection"""
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

class KeywordAnalyzer:
    def __init__(self, llama_analyzer: LlamaAnalyzer):
        self.llama = llama_analyzer
    
    def analyze_product_keywords(self, product: Dict) -> Dict:
        """Extract and analyze keywords from product data"""
        title = product.get('title', '')
        description = product.get('description', '')
        tags = product.get('tags', [])
        
        system_prompt = """You are a keyword research expert. Analyze the product information and:
        1. Extract the most important keywords for SEO and marketing
        2. Identify search intent behind these keywords
        3. Suggest related keywords with high commercial value
        4. Rate keyword difficulty (1-10 scale)
        
        Focus on keywords that buyers would actually use when searching for this product."""
        
        prompt = f"""
        Analyze keywords for this product:
        Title: {title}
        Description: {description[:500]}...
        Tags: {', '.join(tags) if tags else 'None'}
        
        Extract primary keywords, secondary keywords, and long-tail opportunities.
        Rate the commercial value and competition level for each keyword group.
        """
        
        ai_response = self.llama.query_llama(prompt, system_prompt)
        
        return {
            'primary_keywords': self.extract_keywords_from_response(ai_response, 'primary'),
            'secondary_keywords': self.extract_keywords_from_response(ai_response, 'secondary'),
            'long_tail_keywords': self.extract_keywords_from_response(ai_response, 'long-tail'),
            'keyword_analysis': ai_response,
            'commercial_value': self.extract_numeric_score(ai_response, default=5.0)
        }
    
    def extract_keywords_from_response(self, response: str, keyword_type: str) -> List[str]:
        """Extract keywords from AI response based on type"""
        # This is a simplified extraction - you might want to make it more sophisticated
        lines = response.lower().split('\n')
        keywords = []
        
        capture_next = False
        for line in lines:
            if keyword_type in line:
                capture_next = True
                continue
            
            if capture_next and line.strip():
                # Extract keywords from the line
                words = re.findall(r'\b[a-zA-Z\s]{2,30}\b', line)
                keywords.extend([w.strip() for w in words if len(w.strip()) > 2])
                
                if len(keywords) >= 5:  # Limit to reasonable number
                    break
        
        return keywords[:5]  # Return top 5 keywords
    
    def extract_numeric_score(self, text: str, default: float = 5.0) -> float:
        """Extract numeric score from text"""
        patterns = [
            r'commercial value[:\s]+(\d+(?:\.\d+)?)',
            r'value[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)[/\s]*(?:out of |/)?\s*10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return default

# Usage example and main execution
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'ecommerce_research',
        'user': 'researcher',
        'password': 'research123'
    }
    
    # Initialize analyzer
    analyzer = ProductAnalysisEngine(db_config)
    
    try:
        # Example: Analyze products in batch
        print("Starting batch analysis...")
        results = analyzer.batch_analyze_products(limit=50)
        
        print(f"\nBatch Analysis Results:")
        print(f"Total Analyzed: {results.get('total_analyzed', 0)}")
        print(f"High Opportunity: {results.get('high_opportunity', 0)}")
        print(f"Medium Opportunity: {results.get('medium_opportunity', 0)}")
        print(f"Low Opportunity: {results.get('low_opportunity', 0)}")
        
        # Generate market report
        print("\nGenerating market report...")
        report = analyzer.generate_market_report()
        
        if 'error' not in report:
            print(f"Report generated at: {report['report_generated']}")
            print(f"Top opportunities found: {report['summary']['total_high_opportunities']}")
            print(f"Best platform: {report['summary']['best_performing_platform']}")
            print(f"Top category: {report['summary']['top_trending_category']}")
            
            # Show top 3 opportunities
            print("\nTop 3 Opportunities:")
            for i, opp in enumerate(report['top_opportunities'][:3], 1):
                print(f"{i}. {opp['title'][:50]}... | {opp['platform']} | Score: {opp['opportunity_score']}")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
    
    finally:
        analyzer.close_connection()