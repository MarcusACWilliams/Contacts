# Contacts Application - Design Document

## 1. Project Overview

The **Contacts** application is a modern, web-based contact management system built with a FastAPI backend and vanilla HTML/CSS/JavaScript frontend. It enables users to create, read, update, and search contact information with email and phone number validation.

### Key Technologies
- **Backend**: FastAPI (Python async web framework)
- **Database**: MongoDB (async PyMongo client)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (no build tools)
- **Validation**: Pydantic v2 with custom validators
- **Email Validation**: Custom `emailaddress` class with provider detection
- **Deployment**: Uvicorn ASGI server, AWS App Runner

---

## 2. Current Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Static Files)                      │
│  ┌──────────────┐┌──────────────┐┌──────────────────┐           │
│  │ index.html   ││ styles.css   ││ JavaScript Logic │           │
│  │  (React-like)││              ││ (Vanilla AJAX)   │           │
│  └──────────────┘└──────────────┘└──────────────────┘           │
└──────────────────────┬──────────────────────────────────────────┘
                       │ AJAX (JSON)
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Routes:                                                 │    │
│  │  • GET  /              (Serve HTML)                    │    │
│  │  • GET  /contacts/search    (Search/List)             │    │
│  │  • POST /contacts           (Create)                   │    │
│  │  • PUT  /contacts/{id}      (Update)                   │    │
│  │  • DELETE /contacts/{id}    (Delete)                   │    │
│  │  • POST /emails/validate    (Email validation)         │    │
│  │  • GET  /emails/list        (All unique emails)        │    │
│  │  • GET  /users/             (Raw contacts)             │    │
│  │  • GET  /users/names        (Sorted names)             │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────────┘
                       │ PyMongo (Async)
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                   MongoDB Database                               │
│  ┌────────────────────┐ ┌────────────────────┐                 │
│  │ careTeam (DB)      │ │                    │                 │
│  │ ┌──────────────┐   │ │                    │                 │
│  │ │ users (coll) │   │ │ emails (coll)      │                 │
│  │ │              │   │ │                    │                 │
│  │ │  Document:   │   │ │  Document:         │                 │
│  │ │  - _id       │   │ │  - _id             │                 │
│  │ │  - first     │   │ │  - _contact_id     │                 │
│  │ │  - last      │   │ │  - address         │                 │
│  │ │  - emails[]  │   │ │  - type            │                 │
│  │ │  - phone[]   │   │ │                    │                 │
│  │ │  - address   │   │ │                    │                 │
│  │ └──────────────┘   │ │                    │                 │
│  └────────────────────┘ └────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Models

#### Contact Model (`dataModels.py`)
```
Contact
├── _id: str (hex-encoded 12-byte ID)
├── first: str (required, letters/space/hyphen/apostrophe only)
├── last: str (required, letters/space/hyphen/apostrophe only)
├── emails: List[EmailAddress] (validated via emailaddress class)
├── phone: List[str] (digits, spaces, hyphens, parentheses)
├── address: Optional[str]
├── social_media: Optional[dict]
├── notes: Optional[str]
└── birthday: Optional[datetime]
```

#### EmailAddress Model
```
EmailAddress
├── _id: str (hex-encoded 12-byte ID)
├── _contact_id: str (reference to Contact._id)
├── address: str (validated via emailaddress class)
└── type: Optional[str] (default: 'home')
```

### 2.3 ID Generation Strategy

Uses a custom 12-byte ID scheme (MongoDB ObjectId-like):
- **Bytes 0-3**: Unix timestamp (seconds since epoch)
- **Bytes 4-8**: 5-byte random value
- **Bytes 9-11**: 3-byte process-local counter (wraps at 2^24)

Returns as hex string for JSON serialization.

### 2.4 API Response Format

**Success Response:**
```json
{
  "id": "string",
  "message": "Operation successful"
}
```

**Validation Error Response:**
```json
{
  "error": "Validation failed",
  "details": [
    {
      "field": "fieldName",
      "message": "Error description"
    }
  ]
}
```

**Generic Error Response:**
```json
{
  "error": "Error description"
}
```

---

## 3. Current Features (Implemented)

### 3.1 Contact Management (CRUD)
- ✅ **Create Contact**: POST `/contacts` with first, last, emails, phone, address
- ✅ **Read Contact**: GET `/contacts/search` (supports filtering by name)
- ✅ **Update Contact**: PUT `/contacts/{id}` with full contact data
- ✅ **Delete Contact**: DELETE `/contacts/{id}`
- ✅ **List Contacts**: GET `/users/` returns all raw documents
- ✅ **Search Contacts**: Case-insensitive regex search on first/last name

### 3.2 Email Management
- ✅ **Email Validation**: POST `/emails/validate` uses custom `emailaddress` class
- ✅ **Email Collection**: Automatic background task `gatherEmailAddresses()` extracts unique emails
- ✅ **List Unique Emails**: GET `/emails/list` returns all unique emails from all contacts
- ✅ **Email Providers**: GET `/emails/providers` lists 50+ common email providers

### 3.3 Frontend UI
- ✅ **Contact List**: Scrollable list with sorted names (A-Z)
- ✅ **Search Bar**: Real-time search filtering on typing
- ✅ **Add Contact Modal**: Reusable modal for create/edit with validation
- ✅ **Detail View Modal**: Read-only view of contact information
- ✅ **Edit Mode**: Modal automatically loads contact data for editing
- ✅ **Delete Confirmation**: Secondary confirmation modal prevents accidents
- ✅ **Dynamic Field Addition**: Add/remove phone and email fields in form
- ✅ **Phone Number Formatting**: Cleave.js integration for US phone formatting
- ✅ **Avatar Placeholder**: User emoji avatar in detail views

### 3.4 Validation & Error Handling
- ✅ **Name Validation**: Only allows letters, spaces, hyphens, apostrophes
- ✅ **Email Validation**: Custom class validates format and common providers
- ✅ **Phone Validation**: Digits, spaces, hyphens, parentheses only
- ✅ **Custom Exception Handler**: Returns standardized validation error format
- ✅ **CORS Support**: Permissive CORS for AJAX requests

### 3.5 Background Tasks
- ✅ **Email Gathering**: Scheduled background task after create/update
- ✅ **Duplicate Detection** (Disabled): Infrastructure for checking duplicates exists but is not enforced

---

## 4. Proposed Feature: Basic Messaging

### 4.1 Feature Overview
Add the ability to send text messages (SMS) or emails directly from the Contacts app to saved contacts.

### 4.2 Scope & Priorities

#### Phase 1: Email Messaging (Priority: High)
- Send emails to single contact
- Basic email template with contact name
- Email delivery status tracking
- Sent messages log

#### Phase 2: SMS Messaging (Priority: Medium)
- Send SMS to phone number
- Character counting and warnings
- SMS delivery status
- Phone number validation for carrier

#### Phase 3: Message History (Priority: Low)
- View sent/received messages per contact
- Message threading
- Message search

### 4.3 Data Model Extensions

#### New Collection: `messages`
```
Message
├── _id: str (auto-generated hex ID)
├── _contact_id: str (FK to Contact._id)
├── type: str (enum: 'email' | 'sms')
├── direction: str (enum: 'sent' | 'received')
├── recipient: str (email address or phone number)
├── subject: Optional[str] (only for email)
├── body: str (message content)
├── status: str (enum: 'draft' | 'sending' | 'sent' | 'failed' | 'delivered')
├── timestamp: datetime (when message was created/sent)
├── delivered_at: Optional[datetime]
├── error_message: Optional[str] (if status == 'failed')
└── metadata: Optional[dict] (provider info, message ID, etc)
```

#### Updated Contact Model
```
Contact
├── ... (existing fields)
├── messaging_preferences: Optional[dict]
│   ├── preferred_email: Optional[str]
│   ├── preferred_phone: Optional[str]
│   └── do_not_contact: Optional[bool]
└── last_contacted: Optional[datetime]
```

### 4.4 Email Messaging Implementation

#### Backend: New Endpoints

**POST `/messages/email/send`** - Send email to contact
```json
Request:
{
  "contact_id": "string",
  "email": "string",
  "subject": "string",
  "body": "string",
  "is_draft": false
}

Response (Success):
{
  "id": "message_id",
  "status": "sending",
  "message": "Email queued for delivery"
}

Response (Error):
{
  "error": "Invalid email address for contact"
}
```

**POST `/messages/email/draft`** - Save email as draft
```json
Request: (same as /send)
Response: { "id": "draft_id", "status": "draft" }
```

**GET `/messages/contact/{contact_id}`** - Get message history for contact
```json
Response:
{
  "messages": [
    {
      "_id": "string",
      "type": "email",
      "recipient": "user@example.com",
      "subject": "string",
      "body": "string",
      "status": "sent",
      "timestamp": "2026-02-11T12:00:00Z",
      "delivered_at": "2026-02-11T12:05:00Z"
    }
  ]
}
```

**PUT `/messages/{message_id}`** - Update draft message
```json
Request:
{
  "body": "updated message",
  "subject": "updated subject"
}
```

**DELETE `/messages/{message_id}`** - Delete draft message

#### Email Provider Integration

Use Python `smtplib` or third-party service:

**Option A: SMTP (Simple, self-hosted)**
```python
# .env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-password
SENDER_NAME=Contacts App
SENDER_EMAIL=noreply@contacts-app.com
```

**Option B: SendGrid (Recommended for production)**
```python
# .env
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@contacts-app.com
```

**Option C: AWS SES**
```python
# Environment variables or IAM role
AWS_REGION=us-east-1
AWS_SES_FROM_EMAIL=noreply@contacts-app.com
```

#### Email Service Module
Create `classes/messaging.py`:
```python
class EmailMessenger:
    async def send_email(
        contact_id: str,
        recipient_email: str,
        subject: str,
        body: str,
        save_message: bool = True
    ) -> dict:
        """Send email and optionally save to messages collection"""
        # Validate recipient email
        # Build email (basic or HTML template)
        # Send via configured provider
        # Save message record with status
        # Return {id, status, error?}
    
    async def get_template(template_name: str) -> str:
        """Get email template"""
        
    async def render_template(template: str, context: dict) -> str:
        """Render template with contact data"""
```

### 4.5 SMS Messaging Implementation

#### Backend: New Endpoints

**POST `/messages/sms/send`** - Send SMS
```json
Request:
{
  "contact_id": "string",
  "phone": "string",
  "body": "string",
  "is_draft": false
}

Response:
{
  "id": "message_id",
  "status": "sending",
  "character_count": 160,
  "segments": 1,
  "message": "SMS queued for delivery"
}
```

#### SMS Provider Integration

**Twilio (Recommended)**
```python
# .env
TWILIO_ACCOUNT_SID=ACxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_PHONE=+1234567890
```

**AWS SNS**
```python
# AWS credentials
AWS_REGION=us-east-1
```

**MessageBird/Vonage**
```python
MESSAGEBIRD_API_KEY=xxxxx
MESSAGEBIRD_FROM_PHONE=+1234567890
```

### 4.6 Message History & Status Tracking

#### Database Queries
```python
# Get all messages for a contact
db.messages.find({
  "_contact_id": contact_id,
  "direction": "sent"
}).sort("timestamp", -1).limit(50)

# Get failed messages (for retry)
db.messages.find({
  "status": "failed"
}).sort("timestamp", -1)

# Get drafts for user
db.messages.find({
  "status": "draft"
})
```

#### Webhook Handlers
Create endpoint to receive delivery status updates from providers:

**POST `/webhooks/email-delivery`** - For SendGrid/SES webhooks
```json
Request:
{
  "message_id": "string",
  "status": "delivered|bounced|opened|clicked",
  "timestamp": "2026-02-11T12:00:00Z"
}
```

**POST `/webhooks/sms-delivery`** - For Twilio/AWS SNS callbacks
```json
Request:
{
  "message_id": "string",
  "status": "delivered|failed",
  "failure_code": "opt_out|unreachable"
}
```

### 4.7 Frontend UI Changes

#### Contact Detail Modal - Add Messaging Section
```html
<div class="form-section" id="messagingSection">
  <div class="form-section-title">Quick Message</div>
  <div class="message-buttons">
    <button class="btn-message-email" onclick="openEmailComposer()">
      ✉️ Send Email
    </button>
    <button class="btn-message-sms" onclick="openSMSComposer()">
      💬 Send SMS
    </button>
    <button class="btn-message-history" onclick="viewMessageHistory()">
      📋 View History
    </button>
  </div>
</div>
```

#### Email Composer Modal
```html
<div id="emailComposerOverlay" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h2>Send Email to {contact_name}</h2>
      <button onclick="closeEmailComposer()">Done</button>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label>To:</label>
        <select id="recipientEmail" class="form-control">
          <!-- Populated with contact emails -->
        </select>
      </div>
      <div class="form-group">
        <label>Subject:</label>
        <input type="text" id="emailSubject" placeholder="Email subject">
      </div>
      <div class="form-group">
        <label>Message:</label>
        <textarea id="emailBody" rows="6" placeholder="Type message..."></textarea>
      </div>
      <div class="template-suggestions">
        <button type="button" onclick="insertTemplate('greeting')">
          Greeting Template
        </button>
        <button type="button" onclick="insertTemplate('followup')">
          Follow-up Template
        </button>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" onclick="saveDraft()">Save Draft</button>
      <button type="button" onclick="closeEmailComposer()">Cancel</button>
      <button type="button" onclick="sendEmail()" class="btn-submit">
        Send
      </button>
    </div>
  </div>
</div>
```

#### SMS Composer Modal
```html
<div id="smsComposerOverlay" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h2>Send Text to {contact_name}</h2>
    </div>
    <div class="modal-body">
      <div class="form-group">
        <label>To: +{phone_number}</label>
      </div>
      <div class="form-group">
        <textarea id="smsBody" rows="4" placeholder="Type message (160 characters per SMS)..." 
                  maxlength="1600"></textarea>
        <div class="character-counter">
          <span id="charCount">0</span> / 160 characters
          (<span id="segmentCount">1</span> SMS)
        </div>
      </div>
      <div class="template-suggestions">
        <button type="button" onclick="insertSMSTemplate('quick')">
          Quick Thanks
        </button>
        <button type="button" onclick="insertSMSTemplate('meeting')">
          Meeting Reminder
        </button>
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" onclick="closeSMSComposer()">Cancel</button>
      <button type="button" onclick="sendSMS()" class="btn-submit">
        Send SMS
      </button>
    </div>
  </div>
</div>
```

#### Message History Modal
```html
<div id="messageHistoryOverlay" class="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h2>Message History</h2>
    </div>
    <div class="modal-body">
      <div class="message-list" id="messageList">
        <!-- Messages loaded via AJAX -->
      </div>
    </div>
    <div class="modal-footer">
      <button type="button" onclick="closeMessageHistory()">Close</button>
    </div>
  </div>
</div>
```

#### Message Item Template
```html
<div class="message-item {type} {status}">
  <div class="message-meta">
    <div class="message-type-badge">{type.upper()}</div>
    <div class="message-timestamp">{date_time}</div>
    <div class="message-status">{status}</div>
  </div>
  <div class="message-content">
    {subject && <div class="message-subject">{subject}</div>}
    <div class="message-body">{body}</div>
  </div>
</div>
```

### 4.8 Configuration & Environment Variables

Add to `.env`:
```
# Email Configuration
EMAIL_PROVIDER=sendgrid|smtp|aws-ses  # default: sendgrid
SENDGRID_API_KEY=SG.xxxxx
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-password
SENDER_EMAIL=noreply@contacts-app.com
SENDER_NAME=Contacts App

# SMS Configuration
SMS_PROVIDER=twilio|aws-sns|messagebird  # default: twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_PHONE=+1234567890
AWS_REGION=us-east-1

# Message Settings
MAX_DRAFT_MESSAGES_PER_CONTACT=20
MESSAGE_RETENTION_DAYS=90
WEBHOOK_SECRET_EMAIL=xxxxx
WEBHOOK_SECRET_SMS=xxxxx
```

### 4.9 Implementation Roadmap

#### Week 1: Email Foundation
- [ ] Create `Message` data model and database collection
- [ ] Implement email provider abstraction layer
- [ ] Add `POST /messages/email/send` endpoint
- [ ] Add `POST /messages/email/draft` endpoint
- [ ] Add `GET /messages/contact/{id}` endpoint
- [ ] Implement email validation endpoint
- [ ] Unit tests for email service

#### Week 2: Email UI
- [ ] Update Contact detail modal with messaging section
- [ ] Create email composer modal
- [ ] Build email template system
- [ ] Add AJAX handlers for send/draft/history
- [ ] Add success/error toasts for feedback
- [ ] Style messaging UI components

#### Week 3: SMS Foundation
- [ ] Implement SMS provider abstraction
- [ ] Add `POST /messages/sms/send` endpoint
- [ ] Add SMS validation (carrier lookup, opt-in check)
- [ ] Implement character counter & segment calculator
- [ ] Unit tests for SMS service

#### Week 4: SMS UI & Polish
- [ ] Create SMS composer modal
- [ ] Add SMS template system
- [ ] Implement message history view with filtering
- [ ] Add delivery status indicators
- [ ] Performance optimization for large message lists

#### Week 5: Webhooks & Monitoring
- [ ] Implement webhook handlers for delivery status
- [ ] Add message retry logic for failed sends
- [ ] Create admin dashboard for message stats
- [ ] Add logging and error alerts
- [ ] Integration tests

#### Week 6: Documentation & QA
- [ ] API documentation
- [ ] User guide for messaging features
- [ ] Prepare for production deployment
- [ ] Load testing
- [ ] Security audit (API keys, injection protection)

### 4.10 Security Considerations

1. **API Key Protection**
   - Store sensitive keys in `.env` file (not committed to git)
   - Use environment variables for all secrets
   - Rotate API keys periodically

2. **Input Validation**
   - Sanitize message content (prevent injection)
   - Validate email addresses and phone numbers
   - Rate limit message sending (e.g., 10 messages per minute)

3. **Privacy**
   - Encrypt messages in transit (HTTPS only)
   - Consider message encryption at rest
   - Add opt-out/do-not-contact flags
   - Log message sending for audit trail

4. **Webhook Security**
   - Verify webhook signatures from providers
   - Validate webhook source IP addresses
   - Implement CSRF protection for webhook endpoints

5. **Data Retention**
   - Implement message archival/deletion policy
   - GDPR compliance for contact data
   - Clean up failed messages after 30 days

---

## 5. Deployment Considerations

### 5.1 Current Deployment
- AWS App Runner hosting live demo
- MongoDB Atlas (cloud-hosted database)
- Uvicorn ASGI server (port 8080 in container, 8000 locally)

### 5.2 For Messaging Features
- Add environment variables to App Runner configuration
- Whitelist webhook IPs for external services
- Enable CloudWatch logging for message delivery
- Set up monitoring/alerting for failed sends
- Consider message queue (RabbitMQ/Redis) for high volume

---

## 6. Testing Strategy

### Unit Tests
- Email validation service
- SMS character counting & segmentation
- Message model validation
- Provider abstraction layer

### Integration Tests
- Email send workflow end-to-end
- SMS send workflow
- Webhook handlers
- Message history retrieval

### E2E Tests
- Send email from contact detail view
- Send SMS from contact detail view
- View message history
- Verify draft save functionality

---

## 7. Future Enhancements

- **Two-way messaging**: Receive replies to emails/SMS
- **Message templates library**: Save and reuse templates
- **Bulk messaging**: Send to contact groups
- **Scheduled messages**: Schedule sends for later
- **Read receipts**: Track email opens
- **Rich text editor**: Format email bodies
- **Attachment support**: Send files with emails
- **Messaging integrations**: WhatsApp, Telegram, etc.
- **AI suggestions**: Smart reply suggestions
- **Multi-user support**: Shared team inboxes

---

## 8. Related Files Structure

```
contacts/
├── main.py                          (Updated with message endpoints)
├── dataModels.py                    (Add Message model)
├── connection.py                    (Unchanged)
├── classes/
│   ├── emails.py                    (Existing)
│   ├── messaging.py                 (NEW: Email/SMS service)
│   └── message_templates.py         (NEW: Template system)
├── static/
│   ├── index.html                   (Updated with modals)
│   └── css/
│       ├── styles.css               (Updated styling)
│       └── messaging.css            (NEW: Message UI styles)
├── requirements.txt                 (Add: sendgrid, twilio, or equivalents)
├── .env                             (Add: messaging config)
├── tests/
│   ├── test_messaging.py            (NEW)
│   └── test_email_service.py        (NEW)
└── DESIGN.md                        (This file)
```

---

## 9. Summary

The Contacts application successfully implements a full CRUD contact management system with robust email validation and unique email collection features. The proposed messaging feature extends this foundation with email and SMS capabilities, providing users with seamless communication directly from their contact records.

The implementation plan prioritizes email first (simpler, more commonly used) before adding SMS support, with a clear roadmap for phased development over 6 weeks. The modular architecture allows each component (email service, SMS service, UI) to be developed and tested independently.

Key success metrics:
- ✅ Email delivery success rate > 99%
- ✅ SMS delivery within 5 seconds
- ✅ Message history loads in < 1 second
- ✅ No message data loss
- ✅ GDPR compliant data handling
