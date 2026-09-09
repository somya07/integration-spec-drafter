# Ecommerce to ERP Order Integration Specification

## 1. Integration Overview
This document defines the technical specification for integrating orders from the Ecommerce Platform into the ERP system via a webhook-based integration pattern.

**Integration Type:** Webhook (Inbound)
**Direction:** Ecommerce Platform → ERP System
**Data Entity:** Customer Orders
**Trigger:** Order creation/completion event in Ecommerce Platform

---

## 2. Trigger Event

**Event Name:** `order.created` (or `order.completed`)
**Source System:** Ecommerce Platform
**Event Condition:** A new order is successfully created in the Ecommerce Platform
**Delivery Method:** HTTPS POST request to ERP webhook endpoint
**Retry Policy:** Implement exponential backoff with maximum 3 retry attempts (at 5s, 25s, 125s intervals)
**Timeout:** 30 seconds per request

---

## 3. Webhook Endpoint Specification

**ERP Endpoint URL:** `https://[ERP-HOST]/api/v1/orders/webhook`
**HTTP Method:** POST
**Authentication:** Bearer Token (configured in Ecommerce Platform webhook settings)
**Content-Type:** `application/json`
**Expected Response:** HTTP 200 OK with acknowledgment payload

**Response Acknowledgment Format:**
```json
{
  "success": true,
  "order_number": "[sales_order_number]",
  "message": "Order received and queued for processing",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 4. Payload Structure & Field Mapping

### 4.1 Webhook Payload (Inbound from Ecommerce Platform)

```json
{
  "event_type": "order.created",
  "event_id": "[unique_event_identifier]",
  "timestamp": "[ISO 8601 datetime]",
  "order": {
    "order_number": "[string, unique]",
    "order_date": "[datetime, ISO 8601]",
    "customer_name": "[string]",
    "shipping_address": "[string, full address]",
    "billing_address": "[string, full address]",
    "line_items": [
      {
        "sku": "[string, product SKU]",
        "quantity": "[integer]"
      }
    ]
  }
}
```

### 4.2 Field Mapping Table

| Ecommerce Field | ERP Field | Data Type | Transformation/Notes |
|---|---|---|---|
| `order.order_number` | `sales_order_number` | String | Direct mapping (1:1) |
| `order.order_date` | `order_date` | DateTime (ISO 8601) | Direct mapping (1:1) |
| `order.shipping_address` | `ship_to_address` | String | Direct mapping (1:1) |
| `order.billing_address` | `bill_to_address` | String | Direct mapping (1:1) |
| `order.line_items[].sku` | `order_lines[].item_sku` | String | Direct mapping, iterate through array |
| `order.line_items[].quantity` | `order_lines[].quantity` | Integer | Direct mapping, iterate through array |
| N/A | `order_status` | Enum | Set to "new" for all incoming orders |
| `order.customer_name` | N/A | String | Store in custom field or separate customer table if required |

### 4.3 Data Validation Rules

**Required Fields (Must Not Be Null/Empty):**
- `order.order_number` - Must be unique; reject if duplicate exists in ERP
- `order.order_date` - Must be valid ISO 8601 format
- `order.shipping_address` - Minimum 10 characters
- `order.billing_address` - Minimum 10 characters
- `order.line_items` - Must contain at least 1 item
- `order.line_items[].sku` - Must match existing product in ERP product master
- `order.line_items[].quantity` - Must be positive integer (≥ 1)

**Format Validation:**
- `order_date` - ISO 8601 compliant (YYYY-MM-DDTHH:mm:ssZ)
- `order_number` - Alphanumeric, max 50 characters, no special characters except hyphens and underscores
- Addresses - ASCII text only, max 500 characters each

---

## 5. Error Handling & Exception Flow

### 5.1 Error Classification & Handling

| Error Category | HTTP Code | Handling Action | Retry |
|---|---|---|---|
| **Validation Error** | 400 | Log error, do NOT create order, send error notification to Ecommerce team | No |
| **Duplicate Order** | 409 | Log as warning, return 200 OK (idempotent), do NOT create duplicate | No |
| **Product SKU Not Found** | 422 | Log error, queue order in "pending_validation" state, notify ops team | Yes (after 1 hour) |
| **Authentication Failed** | 401 | Log security event, reject request | No |
| **Rate Limit Exceeded** | 429 | Reject with Retry-After header, implement exponential backoff | Yes |
| **Server Error** | 500 | Log error, queue for retry | Yes (up to 3 times) |
| **Timeout** | 504 | Treat as transient, queue for retry | Yes (up to 3 times) |

### 5.2 Error Response Format

```json
{
  "success": false,
  "order_number": "[order_number if available]",
  "error_code": "[ERROR_CODE]",
  "error_message": "[Human readable error message]",
  "details": {
    "field": "[field_name]",
    "reason": "[Specific validation failure]"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 5.3 Error Logging & Monitoring

**Log Level:** ERROR (for failures)
**Log Details to Capture:**
- Event ID
- Order Number
- Ecommerce Platform IP/Source
- Full payload (sanitized)
- Error stack trace
- Resolution steps taken
- Timestamp
- Retry attempt count

**Monitoring Alerts:**
- More than 5 errors in 15-minute window → Alert Ops Team
- Duplicate order attempt → Alert Ecommerce Team
- SKU validation failure → Alert Product/Inventory Team

---

## 6. Data Processing Flow

```
[Ecommerce Platform]
        ↓ (Webhook POST)
[ERP Webhook Receiver]
        ↓
[Payload Validation]
        ├─ Failed → Log error, return 400/422
        └─ Success ↓
[Duplicate Check]
        ├─ Duplicate found → Log warning, return 200 OK (idempotent)
        └─ New order ↓
[SKU Validation]
        ├─ Invalid SKU → Queue for manual review, return 202 Accepted
        └─ Valid ↓
[Field Mapping & Transform]
        ↓
[Create Sales Order in ERP]
        ├─ order_status = "new"
        └─ Timestamp order creation ↓
[Return 200 OK with Acknowledgment]
        ↓
[Queue Background Job for Fulfillment Processing]
```

---

## 7. Integration Testing Strategy

### 7.1 Test Cases

**Test 1: Happy Path - Valid Order**
- Input: Complete valid payload with all required fields
- Expected Output: HTTP 200 OK, order created in ERP with status "new"

**Test 2: Duplicate Order**
- Input: Same order_number submitted twice
- Expected Output: HTTP 200 OK (idempotent), single order in ERP

**Test 3: Missing Required Field**
- Input: Payload missing shipping_address
- Expected Output: HTTP 400 Bad Request, order NOT created, error details provided

**Test 4: Invalid SKU**
- Input: line_items contains SKU not in product master
- Expected Output: HTTP 422 Unprocessable Entity, order queued for manual review

**Test 5: Malformed JSON**
- Input: Invalid JSON structure
- Expected Output: HTTP 400 Bad Request

**Test 6: Invalid Date Format**
- Input: order_date not in ISO 8601 format
- Expected Output: HTTP 400 Bad Request

**Test 7: Empty Line Items**
- Input: line_items array is empty
- Expected Output: HTTP 400 Bad Request

**Test 8: Negative Quantity**
- Input: quantity value is negative
- Expected Output: HTTP 400 Bad Request

**Test 9: Timeout Scenario**
- Input: ERP processing takes >30 seconds
- Expected Output: Webhook times out, retry triggered automatically

**Test 10: Authentication Failure**
- Input: Invalid or missing Bearer token
- Expected Output: HTTP 401 Unauthorized

---

## 8. Performance & SLA Requirements

**Expected Order Volume:** [TO BE CONFIGURED]
**Throughput Target:** Orders processed within 2 seconds of webhook receipt
**Processing SLA:** 99.5% of orders processed successfully within 5 minutes
**Peak Load Handling:** Support minimum 100 concurrent webhook requests
**Database Transaction Timeout:** 30 seconds per order creation
**Audit Trail:** Maintain complete audit log for minimum 90 days

---

## 9. Security Considerations

**Authentication:**
- Webhook endpoint protected by Bearer Token authentication
- Token stored securely in Ecommerce Platform configuration
- Token rotation recommended every 90 days

**Data Protection:**
- All payloads transmitted over HTTPS with TLS 1.2+
- No sensitive customer data (credit cards, passwords) in payload
- IP whitelisting recommended for Ecommerce Platform source

**Audit & Compliance:**
- All webhook requests logged with source, timestamp, and outcome
- Sensitive fields (addresses) NOT logged in plain text
- PII handling compliant with GDPR/local privacy regulations

---

## 10. Webhook Configuration (Ecommerce Platform)

**Setup Instructions for Ecommerce Platform Admin:**

1. Navigate to: **Settings → Integrations → Webhooks**
2. Click **Add New Webhook**
3. Configure:
   - **Event Type:** `order.created`
   - **Target URL:** `https://[ERP-HOST]/api/v1/orders/webhook`
   - **Authentication Type:** Bearer Token
   - **Token:** [Provide secure token from ERP team]
   - **Content Type:** JSON
   - **Retry Enabled:** Yes
   - **Max Retries:** 3

4. Click **Test** to verify connectivity
5. Click **Save**

---

## 11. Rollback & Disaster Recovery

**Rollback Procedure:**
1. Disable webhook in Ecommerce Platform (Settings → Integrations → Webhooks → Disable)
2. Manually process pending orders in ERP
3. Generate reconciliation report comparing Ecommerce orders vs ERP orders for previous 24 hours
4. Investigate any discrepancies

**Data Recovery:**
- ERP order records are recoverable from daily database backups
- Event ID from webhook payload enables order tracing through both systems
- Webhook request/response logs retained for 90 days for audit trail

---

## 12. Future Enhancements (Out of Scope - Phase 2)

- Order status synchronization back to Ecommerce Platform
- Inventory synchronization
- Shipping tracking integration
- Customer profile synchronization
- Real-time order cancellation handling

---

## Appendix A: Example Webhook Payloads

### Example 1: Single Item Order
```json
{
  "event_type": "order.created",
  "event_id": "evt_1234567890",
  "timestamp": "2024-01-15T10:30:00Z",
  "order": {
    "order_number": "ORD-2024-001234",
    "order_date": "2024-01-15T10:25:00Z",
    "customer_name": "John Doe",
    "shipping_address": "123 Main St, New York, NY 10001, USA",
    "billing_address": "123 Main St, New York, NY 10001, USA",
    "line_items": [
      {
        "sku": "PROD-SKU-12345",
        "quantity": 2
      }
    ]
  }
}
```

### Example 2: Multi-Item Order
```json
{
  "event_type": "order.created",
  "event_id": "evt_9876543210",
  "timestamp": "2024-01-15T11:45:00Z",
  "order": {
    "order_number": "ORD-2024-001235",
    "order_date": "2024-01-15T11:40:00Z",
    "customer_name": "Jane Smith",
    "shipping_address": "456 Oak Ave, Los Angeles, CA 90001, USA",
    "billing_address": "789 Pine Rd, Los Angeles, CA 90002, USA",
    "line_items": [
      {
        "sku": "PROD-SKU-22222",
        "quantity": 1
      },
      {
        "sku": "PROD-SKU-33333",
        "quantity": 3
      },
      {
        "sku": "PROD-SKU-44444",
        "quantity": 1
      }
    ]
  }
}
```

---

## Appendix B: Implementation Checklist

- [ ] ERP webhook endpoint developed and deployed
- [ ] API authentication (Bearer token) implemented
- [ ] Field mapping logic implemented in ERP receiver
- [ ] Validation rules implemented for all required fields
- [ ] Error handling and retry logic implemented
- [ ] Logging and monitoring configured
- [ ] Database schema updated to support order imports
- [ ] Integration testing completed (all 10 test cases passed)
- [ ] Load testing performed (100+ concurrent requests)
- [ ] Security review completed
- [ ] Webhook configured in Ecommerce Platform
- [ ] UAT testing completed with sample orders
- [ ] Runbook documentation created for ops team
- [ ] Production deployment completed
- [ ] Monitoring dashboards configured
- [ ] Stakeholder communication completed

