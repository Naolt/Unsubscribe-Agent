# Domain Unsubscription API

The Domain Unsubscription API allows you to unsubscribe from marketing emails by providing just a domain name and your email address. The system will automatically discover unsubscribe pages and attempt unsubscription.

## Features

- **Intelligent URL Discovery**: Automatically finds unsubscribe pages from domain crawling
- **Cache-First Approach**: Uses cached results when available, only crawls when needed
- **Page Exploration**: Can explore privacy pages, contact pages, and other non-direct unsubscribe pages
- **Structured Results**: Returns detailed information about the unsubscription process
- **Domain Index Updates**: Automatically updates the domain index with successful discoveries

## API Endpoints

### POST `/unsubscribe/domain`

Unsubscribe from a domain using discovered unsubscribe pages.

**Request Body:**
```json
{
  "domain": "example.com",
  "user_email": "user@example.com",
  "force_refresh": false,
  "crawl_options": {
    "max_pages": 10,
    "max_depth": 3,
    "include_subdomains": false
  }
}
```

**Response:**
```json
{
  "status": "PENDING",
  "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
  "message": "Domain unsubscription queued for processing (3 URLs found)",
  "domain": "example.com",
  "user_email": "user@example.com",
  "unsubscribe_urls": [
    "https://example.com/unsubscribe",
    "https://example.com/privacy",
    "https://example.com/contact"
  ],
  "confident_url": "https://example.com/unsubscribe"
}
```

### GET `/unsubscribe/task/{task_id}`

Get the status of a domain unsubscription task.

**Response:**
```json
{
  "status": "SUCCESS",
  "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
  "message": "Task completed successfully",
  "result": {
    "success": true,
    "message": "Processed 3 URLs: 1 successful, 2 failed",
    "domain": "example.com",
    "user_email": "user@example.com",
    "unsubscribe_urls_found": 3,
    "urls_attempted": 3,
    "successful_unsubscribes": 1,
    "failed_unsubscribes": 2,
    "results": [
      {
        "original_url": "https://example.com/unsubscribe",
        "final_url": "https://example.com/preferences/unsubscribe",
        "discovered_url": "https://example.com/preferences/unsubscribe",
        "url_type": "confident_unsubscribe",
        "confidence": 0.9,
        "success": true,
        "message": "Successfully unsubscribed from all marketing emails",
        "method": "https",
        "page_type": "unsubscribe",
        "login_required": false,
        "multiple_subscriptions": true,
        "actions_taken": ["entered email", "clicked unsubscribe button", "confirmed unsubscription"]
      }
    ]
  }
}
```

### GET `/unsubscribe/domain/{domain}`

Check if a domain has cached unsubscribe URLs.

**Response:**
```json
{
  "domain": "example.com",
  "found": true,
  "unsubscribe_url": "https://example.com/unsubscribe",
  "confidence": 0.9,
  "discovered_at": "2024-01-15T10:30:00Z",
  "last_verified": "2024-01-15T10:30:00Z",
  "query_time": "2024-01-15T11:00:00Z"
}
```

## How It Works

### 1. Cache Check
- First checks if the domain has cached unsubscribe URLs
- Uses cached results if available and not stale
- Only proceeds to crawling if no cache or force_refresh=true

### 2. Domain Discovery
- Crawls the domain to find unsubscribe pages
- Uses breadth-first search to explore the website
- Identifies pages with unsubscribe forms or links

### 3. Intelligent URL Selection
- Prioritizes URLs by confidence score
- Tries confident unsubscribe URLs first
- Falls back to privacy/contact pages if needed

### 4. Enhanced Browser Automation
- Uses AI-powered browser automation to explore pages
- Can navigate from privacy pages to unsubscribe pages
- Detects login requirements and stops if needed
- Handles multiple subscription types

### 5. Structured Results
- Returns detailed information about each attempt
- Includes discovered URLs and page types
- Tracks actions taken during unsubscription
- Updates domain index with successful discoveries

## Page Types Handled

- **Unsubscribe Pages**: Direct unsubscribe forms
- **Privacy Policy Pages**: Often contain unsubscribe links
- **Contact Pages**: May have email preference options
- **Homepage**: Footer links to unsubscribe pages
- **Terms of Service**: Sometimes contain unsubscribe information

## Error Handling

- **Login Required**: Stops if authentication is needed
- **No Unsubscribe Options**: Reports when no options are found
- **Complex Verification**: Handles CAPTCHAs and complex forms
- **Untrusted Sites**: Identifies and avoids suspicious sites

## Examples

### Basic Unsubscription
```bash
curl -X POST "http://localhost:8000/unsubscribe/domain" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "newsletter.com",
    "user_email": "user@example.com"
  }'
```

### Force Refresh Cache
```bash
curl -X POST "http://localhost:8000/unsubscribe/domain" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "newsletter.com",
    "user_email": "user@example.com",
    "force_refresh": true
  }'
```

### Custom Crawl Options
```bash
curl -X POST "http://localhost:8000/unsubscribe/domain" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "newsletter.com",
    "user_email": "user@example.com",
    "crawl_options": {
      "max_pages": 20,
      "max_depth": 4,
      "include_subdomains": true
    }
  }'
```

## Integration with Existing Systems

The Domain Unsubscription API integrates seamlessly with:

- **Domain Discovery API**: Uses the same crawling infrastructure
- **Email Processing API**: Shares the same unsubscription logic
- **Task Management**: Uses the same Celery task system
- **Domain Index**: Updates the same cache system

## Best Practices

1. **Use Cache First**: Don't set `force_refresh=true` unless necessary
2. **Monitor Task Status**: Always check task status after submission
3. **Handle Errors Gracefully**: Check for login requirements and other limitations
4. **Batch Processing**: Consider batching multiple domains for efficiency
5. **Update Cache**: The system automatically updates the domain index with successful discoveries
