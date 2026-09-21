with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the query template
start = content.find('HTTP_ARCHIVE_QUERY = """')
if start >= 0:
    end = content.find('"""', start + 20)
    if end == -1:
        end = content.find('\n"""', start + 20)
    
    if end >= 0:
        old_query = content[start:end+3]
        print('Found query, length:', len(old_query))
        
        # New query with fixed regex escaping
        new_query = '''HTTP_ARCHIVE_QUERY = """
-- HTTP Archive BigQuery Extraction Query
-- Extracts page-level data from HTTP Archive summary_pages table
-- Maps to Tracera's 17-feature schema

WITH
-- Base page data from HTTP Archive summary_pages
base_pages AS (
    SELECT
        page,
        url,
        status_code,
        content_type,
        mime_type,
        response_headers,
        request_headers,
        first_html,
        is_root_page,
        load_time,
        page_size,
        crawl_time,
        client
    FROM `{project_id}.{dataset_id}.{table_prefix}{client}`
    WHERE 
        status_code = 200
        AND (mime_type LIKE 'text/html%' OR mime_type LIKE 'application/xhtml+xml%')
        AND is_root_page = true
),

-- Parse response headers from JSON array
headers_parsed AS (
    SELECT
        *,
        (
            SELECT ARRAY_AGG(STRUCT(
                LOWER(JSON_EXTRACT_SCALAR(h, '$.name')) as name,
                JSON_EXTRACT_SCALAR(h, '$.value') as value
            ))
            FROM UNNEST(JSON_QUERY_ARRAY(response_headers)) as h
        ) as parsed_response_headers
    FROM base_pages
),

-- Extract individual header values
headers_extracted AS (
    SELECT
        *,
        MAX(CASE WHEN LOWER(name) = 'strict-transport-security' THEN 1 ELSE 0 END) as hsts_present,
        MAX(CASE WHEN LOWER(name) = 'content-security-policy' THEN 1 ELSE 0 END) as csp_present,
        MAX(CASE WHEN LOWER(name) = 'x-content-type-options' AND LOWER(value) = 'nosniff' THEN 1 ELSE 0 END) as x_content_type_options_present,
        MAX(CASE WHEN LOWER(name) = 'x-frame-options' THEN 1 ELSE 0 END) as x_frame_options_present,
        MAX(CASE WHEN LOWER(name) = 'referrer-policy' THEN 1 ELSE 0 END) as referrer_policy_present,
        MAX(CASE WHEN LOWER(name) = 'permissions-policy' THEN 1 ELSE 0 END) as permissions_policy_present,
        MAX(CASE WHEN LOWER(name) = 'server' THEN 1 ELSE 0 END) as server_header_present,
        MAX(CASE WHEN LOWER(name) = 'server' THEN value END) as server_header_value,
        MAX(CASE WHEN LOWER(name) = 'x-powered-by' THEN 1 ELSE 0 END) as x_powered_by_present,
        MAX(CASE WHEN LOWER(name) = 'x-powered-by' THEN value END) as x_powered_by_value,
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
        (
            SELECT COUNT(*)
            FROM UNNEST(cookie_headers) as cookie
        ) as cookie_count,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), ';\\\\s*secure\\\\b')
                )
            ELSE 0.0
        END as cookie_secure_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), ';\\\\s*httponly\\\\b')
                )
            ELSE 0.0
        END as cookie_httponly_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), ';\\\\s*samesite\\\\s*=\\\\s*strict\\\\b')
                )
            ELSE 0.0
        END as cookie_samesite_strict_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), ';\\\\s*samesite\\\\s*=\\\\s*lax\\\\b')
                )
            ELSE 0.0
        END as cookie_samesite_lax_ratio,
        
        CASE 
            WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN
                (
                    SELECT COUNT(*) / CAST(ARRAY_LENGTH(cookie_headers) AS FLOAT64)
                    FROM UNNEST(cookie_headers) as cookie
                    WHERE REGEXP_CONTAINS(LOWER(cookie), ';\\\\s*samesite\\\\s*=\\\\s*none\\\\b')
                )
            ELSE 0.0
        END as cookie_samesite_none_ratio,
        
        CASE WHEN ARRAY_LENGTH(cookie_headers) > 0 THEN TRUE ELSE FALSE END as cookie_info_available
    FROM headers_extracted
),

-- Origin normalization
origins_normalized AS (
    SELECT
        *,
        CONCAT(
            REGEXP_EXTRACT(url, '^(https?://[^/]+)'),
            IF(REGEXP_CONTAINS(url, '^https?://[^/]+:\\\\d+'), 
               REGEXP_EXTRACT(url, ':(\\\\d+)(?:/|$)'),
               IF(STARTS_WITH(url, 'https://'), ':443', ':80'))
        ) as origin,
        REGEXP_EXTRACT(url, '^https?://([^/]+)') as hostname,
        REGEXP_EXTRACT(url, '^(https?)://') as scheme
    FROM cookies_parsed
),

-- Extract registrable domain with cloud platform handling
origins_with_registrable AS (
    SELECT
        *,
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
            ELSE REGEXP_EXTRACT(hostname, '([^.]+\\\\.[^.]+)$')
        END as registrable_domain
    FROM (
        SELECT
            *,
            CONCAT(
                REGEXP_EXTRACT(url, '^(https?://[^/]+)'),
                IF(REGEXP_CONTAINS(url, '^https?://[^/]+:\\\\d+'), 
                   REGEXP_EXTRACT(url, ':(\\\\d+)(?:/|$)'),
                   IF(STARTS_WITH(url, 'https://'), ':443', ':80'))
            ) as origin,
            REGEXP_EXTRACT(url, '^https?://([^/]+)') as hostname,
            REGEXP_EXTRACT(url, '^(https?)://') as scheme
        ) as normalized
        FROM cookies_parsed
    ) normalized
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
'''

# Find the old query and replace it
start_idx = content.find('HTTP_ARCHIVE_QUERY = """')
end_idx = content.find('"""', start_idx + 20)
if end_idx == -1:
    end_idx = content.find('\n"""', start_idx + 20)

if start_idx >= 0 and end_idx >= 0:
    new_content = content[:start_idx] + new_query + content[end_idx+3:]
    with open(r'C:\Tracera\ml\data\http_archive\extract.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Query updated successfully!')
else:
    print('Could not find query template')
"