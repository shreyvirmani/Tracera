-- HTTP Archive BigQuery Extraction Query
-- Extracts page-level data from HTTP Archive summary_pages table
-- Maps to Tracera's 17-feature schema
--
-- Configuration variables (set via BigQuery parameterized queries or templating):
-- @project_id: BigQuery project ID (e.g., 'httparchive')
-- @dataset_id: BigQuery dataset (e.g., 'summary_pages')
-- @table_prefix: Table prefix for crawl date (e.g., '2025_07_01_')
-- @client: 'desktop' or 'mobile'
-- @limit: Maximum number of rows to return
-- @random_seed: Random seed for sampling

WITH
-- Base page data from HTTP Archive summary_pages
base_pages AS (
    SELECT
        -- Page identification
        page,
        url,
        
        -- Response metadata
        status_code,
        content_type,
        mime_type,
        
        -- Response headers (JSON array of objects with name/value)
        response_headers,
        
        -- Request metadata
        request_headers,
        
        -- Page metadata
        first_html,
        is_root_page,
        
        -- Timing
        load_time,
        
        -- Size
        page_size,
        
        -- Crawl metadata
        crawl_time,
        
        -- Client type
        client
    FROM `{project_id}.{dataset_id}.{table_prefix}{client}`
    WHERE 
        -- Only successful responses
        status_code = 200
        -- Only HTML content
        AND (mime_type LIKE 'text/html%' OR mime_type LIKE 'application/xhtml+xml%')
        -- Only root pages (first HTML document for the origin)
        AND is_root_page = true
),

-- Extract and parse headers
headers_parsed AS (
    SELECT
        *,
        -- Parse response headers from JSON array
        -- HTTP Archive stores headers as array of {name, value} objects
        (
            SELECT ARRAY_AGG(STRUCT(
                LOWER(JSON_EXTRACT_SCALAR(h, '$.name')) as name,
                JSON_EXTRACT_SCALAR(h, '$.value') as value
            ))
            FROM UNNEST(JSON_QUERY_ARRAY(response_headers)) as h
        ) as parsed_response_headers,
        
        (
            SELECT ARRAY_AGG(STRUCT(
                LOWER(JSON_EXTRACT_SCALAR(h, '$.name')) as name,
                JSON_EXTRACT_SCALAR(h, '$.value') as value
            ))
            FROM UNNEST(JSON_QUERY_ARRAY(request_headers)) as h
        ) as parsed_request_headers
    FROM base_pages
),

-- Extract individual header values
headers_extracted AS (
    SELECT
        *,
        -- Security headers
        MAX(CASE WHEN LOWER(name) = 'strict-transport-security' THEN 1 ELSE 0 END) as hsts_present,
        MAX(CASE WHEN LOWER(name) = 'content-security-policy' THEN 1 ELSE 0 END) as csp_present,
        MAX(CASE WHEN LOWER(name) = 'x-content-type-options' AND LOWER(value) = 'nosniff' THEN 1 ELSE 0 END) as x_content_type_options_present,
        MAX(CASE WHEN LOWER(name) = 'x-frame-options' THEN 1 ELSE 0 END) as x_frame_options_present,
        MAX(CASE WHEN LOWER(name) = 'referrer-policy' THEN 1 ELSE 0 END) as referrer_policy_present,
        MAX(CASE WHEN LOWER(name) = 'permissions-policy' THEN 1 ELSE 0 END) as permissions_policy_present,
        
        -- Tech disclosure
        MAX(CASE WHEN LOWER(name) = 'server' THEN 1 ELSE 0 END) as server_header_present,
        MAX(CASE WHEN LOWER(name) = 'server' THEN value END) as server_header_value,
        MAX(CASE WHEN LOWER(name) = 'x-powered-by' THEN 1 ELSE 0 END) as x_powered_by_present,
        MAX(CASE WHEN LOWER(name) = 'x-powered-by' THEN value END) as x_powered_by_value,
        
        -- Cookie parsing
        -- Collect all Set-Cookie headers
        ARRAY_AGG(
            CASE 
                WHEN LOWER(name) = 'set-cookie' THEN value 
                ELSE NULL 
            END IGNORE NULLS
        ) as cookie_headers
    FROM headers_parsed,
    UNNEST(parsed_response_headers) as h(name, value)
    GROUP BY page, url, status_code, content_type, mime_type, 
             first_html, is_root_page, load_time, page_size, crawl_time, client
),

-- Parse cookies
cookies_parsed AS (
    SELECT
        *,
        -- Parse individual cookies
        (
            SELECT COUNT(*)
            FROM UNNEST(cookie_headers) as cookie
        ) as cookie_count,
        
        -- Secure flag
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), r';\s*secure\b')
                )
            ELSE 0.0
        END as cookie_secure_ratio,
        
        -- HttpOnly flag
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), r';\s*httponly\b')
                )
            ELSE 0.0
        END as cookie_httponly_ratio,
        
        -- SameSite attributes
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), r';\s*samesite\s*=\s*strict\b')
                )
            ELSE 0.0
        END as cookie_samesite_strict_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), r';\s*samesite\s*=\s*lax\b')
                )
            ELSE 0.0
        END as cookie_samesite_lax_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), r';\s*samesite\s*=\s*none\b')
                )
            ELSE 0.0
        END as cookie_samesite_none_ratio,
        
        -- Cookie info availability flag
        CASE WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN TRUE ELSE FALSE END as cookie_info_available
    FROM headers_extracted
),

-- Origin normalization and deduplication
origins_normalized AS (
    SELECT
        *,
        -- Extract origin from URL
        CONCAT(
            REGEXP_EXTRACT(url, r'^(https?://[^/]+)'),
            IF(REGEXP_CONTAINS(url, r'^https?://[^/]+:\d+'), 
               REGEXP_EXTRACT(url, r':(\d+)(?:/|$)'),
               IF(STARTS_WITH(url, 'https://'), ':443', ':80'))
        ) as origin,
        
        -- Extract hostname
        REGEXP_EXTRACT(url, r'^https?://([^/]+)') as hostname,
        
        -- URL scheme
        REGEXP_EXTRACT(url, r'^(https?)://') as scheme
    FROM cookies_parsed
),

-- Extract registrable domain (eTLD+1) with cloud platform handling
origins_with_registrable AS (
    SELECT
        *,
        -- Determine if this is a known cloud platform
        CASE
            WHEN ENDS_WITH(hostname, '.github.io') THEN 'github.io'
            WHEN ENDS_WITH(hostname, '.herokuapp.com') THEN 'herokuapp.com'
            WHEN ENDS_WITH(hostname, '.azurewebsites.net') THEN 'azurewebsites.net'
            WHEN ENDS_WITH(hostname, '.blogspot.com') THEN 'blogspot.com'
            WHEN ENDS_WITH(hostname, '.netlify.app') THEN 'netlify.app'
            WHEN ENDS_WITH(hostname, '.vercel.app') THEN 'vercel.app'
            WHEN ENDS_WITH(hostname, '.pages.dev') THEN 'pages.dev'
            WHEN ENDS_WITH(hostname, '.firebaseapp.com') THEN 'firebaseapp.com'
            WHEN ENDS_WITH(hostname, '.amazonaws.com') THEN 'amazonaws.com'
            WHEN ENDS_WITH(hostname, '.cloudfront.net') THEN 'cloudfront.net'
            WHEN ENDS_WITH(hostname, '.netlify.app') THEN 'netlify.app'
            WHEN ENDS_WITH(hostname, '.vercel.app') THEN 'vercel.app'
            WHEN ENDS_WITH(hostname, '.herokuapp.com') THEN 'herokuapp.com'
            WHEN ENDS_WITH(hostname, '.azurewebsites.net') THEN 'azurewebsites.net'
            ELSE NULL
        END as cloud_platform,
        
        -- Extract registrable domain (eTLD+1)
        -- For cloud platforms, use the platform domain
        CASE
            WHEN ENDS_WITH(hostname, '.github.io') THEN 'github.io'
            WHEN ENDS_WITH(hostname, '.herokuapp.com') THEN 'herokuapp.com'
            WHEN ENDS_WITH(hostname, '.azurewebsites.net') THEN 'azurewebsites.net'
            WHEN ENDS_WITH(hostname, '.blogspot.com') THEN 'blogspot.com'
            WHEN ENDS_WITH(hostname, '.netlify.app') THEN 'netlify.app'
            WHEN ENDS_WITH(hostname, '.vercel.app') THEN 'vercel.app'
            WHEN ENDS_WITH(hostname, '.pages.dev') THEN 'pages.dev'
            WHEN ENDS_WITH(hostname, '.firebaseapp.com') THEN 'firebaseapp.com'
            WHEN ENDS_WITH(hostname, '.amazonaws.com') THEN 'amazonaws.com'
            WHEN ENDS_WITH(hostname, '.cloudfront.net') THEN 'cloudfront.net'
            WHEN ENDS_WITH(hostname, '.netlify.app') THEN 'netlify.app'
            WHEN ENDS_WITH(hostname, '.vercel.app') THEN 'vercel.app'
            WHEN ENDS_WITH(hostname, '.herokuapp.com') THEN 'herokuapp.com'
            WHEN ENDS_WITH(hostname, '.azurewebsites.net') THEN 'azurewebsites.net'
            ELSE REGEXP_EXTRACT(hostname, r'([^.]+\.[^.]+)$')
        END as registrable_domain
    FROM origins_normalized
),

-- Sampling and final selection
sampled_origins AS (
    SELECT *
    FROM origins_with_registrable
    WHERE RAND() < 0.01  -- 1% sample for testing, adjust for production
    LIMIT 10000
)

-- Final output with all 17 features + metadata
SELECT
    -- 17 Model Features (in schema_v1 order)
    status_code,
    1 as is_html,
    CASE WHEN scheme = 'https' THEN 1 ELSE 0 END as https_enabled,
    hsts_present,
    csp_present,
    x_content_type_options_present,
    x_frame_options_present,
    referrer_policy_present,
    permissions_policy_present,
    cookie_count,
    cookie_secure_ratio,
    cookie_httponly_ratio,
    cookie_samesite_strict_ratio,
    cookie_samesite_lax_ratio,
    cookie_samesite_none_ratio,
    server_header_present,
    x_powered_by_present,
    
    -- Metadata (not for model)
    url,
    origin,
    registrable_domain,
    crawl_time as crawl_timestamp,
    page as record_id,
    server_header_value,
    x_powered_by_value,
    content_type,
    cookie_info_available,
    client,
    registrable_domain as registrable_domain_for_grouping
FROM sampled_origins
ORDER BY RAND()