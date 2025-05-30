-- Database initialization script
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    sales_count INTEGER,
    rating DECIMAL(3,2),
    review_count INTEGER,
    seller_info TEXT,
    product_url TEXT,
    image_urls TEXT[],
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_metrics (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    date_analyzed DATE DEFAULT CURRENT_DATE,
    trend_score DECIMAL(5,2),
    competition_level VARCHAR(20),
    profit_potential DECIMAL(5,2),
    market_demand DECIMAL(5,2),
    keyword_difficulty DECIMAL(5,2),
    ai_recommendation TEXT,
    opportunity_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(200) NOT NULL,
    platform VARCHAR(50),
    search_volume INTEGER,
    competition_score DECIMAL(3,2),
    trend_direction VARCHAR(20),
    related_products INTEGER[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(100),
    platforms TEXT[],
    keywords_searched TEXT[],
    products_found INTEGER,
    opportunities_identified INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_products_platform ON products(platform);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_created_at ON products(created_at);
CREATE INDEX idx_product_metrics_opportunity_score ON product_metrics(opportunity_score);
CREATE INDEX idx_keywords_platform ON keywords(platform);

-- Views for analysis
CREATE VIEW winning_products AS
SELECT 
    p.*,
    pm.opportunity_score,
    pm.trend_score,
    pm.profit_potential,
    pm.ai_recommendation
FROM products p
JOIN product_metrics pm ON p.id = pm.product_id
WHERE pm.opportunity_score >= 7.0
ORDER BY pm.opportunity_score DESC;

CREATE VIEW platform_summary AS
SELECT 
    platform,
    COUNT(*) as total_products,
    AVG(price) as avg_price,
    AVG(pm.opportunity_score) as avg_opportunity_score,
    COUNT(CASE WHEN pm.opportunity_score >= 7.0 THEN 1 END) as winning_products_count
FROM products p
JOIN product_metrics pm ON p.id = pm.product_id
GROUP BY platform;