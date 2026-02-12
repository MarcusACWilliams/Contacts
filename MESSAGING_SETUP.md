# Email Messaging Feature - Setup Guide

## Overview
The Contacts app now supports direct email sending to contacts. You can compose and send emails directly from a contact's detail view, save drafts, and view message history.

## Features Implemented
- ✅ Send emails to contact email addresses
- ✅ Email composer with subject and body
- ✅ Save email drafts
- ✅ Message history with status tracking
- ✅ Email templates (greeting, follow-up, quick note)
- ✅ Support for multiple email providers (SMTP, SendGrid)

## Configuration

### 1. Set Up Your Email Provider

#### Option A: Gmail SMTP (Easiest for Testing)

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate an App Password**:
   - Go to https://myaccount.google.com/security
   - Click "2-Step Verification"
   - Scroll to "App passwords"
   - Select app: "Mail", device: "Other" (enter "Contacts App")
   - Copy the 16-character password

3. **Update your `.env` file**:
```bash
EMAIL_PROVIDER=smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SENDER_EMAIL=your-email@gmail.com
SENDER_NAME=Your Name
```

#### Option B: SendGrid (Recommended for Production)

1. **Sign up for SendGrid** at https://sendgrid.com/
2. **Create an API Key**:
   - Go to Settings > API Keys
   - Click "Create API Key"
   - Give it "Full Access" or "Mail Send" permissions
   - Copy the API key

3. **Update your `.env` file**:
```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.your-api-key-here
SENDER_EMAIL=noreply@yourdomain.com
SENDER_NAME=Contacts App
```

4. **Install SendGrid**:
```bash
pip install sendgrid
```

#### Option C: Outlook/Office 365 SMTP

```bash
EMAIL_PROVIDER=smtp
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SENDER_EMAIL=your-email@outlook.com
SENDER_NAME=Your Name
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Restart the Application

```bash
make run-uvicorn
# or
python main.py
```

## Usage

### Sending an Email

1. **Open a contact** from the contacts list
2. **Click "✉️ Send Email"** button in the messaging section
3. **Select recipient email** (if contact has multiple)
4. **Enter subject** and message
5. **Click "Send"** or **"Save Draft"**

### Using Templates

Click one of the template buttons:
- **👋 Greeting**: Friendly greeting message
- **📞 Follow-up**: Follow-up on previous conversation
- **📝 Quick Note**: Short note or reminder

Templates will auto-fill the message body with your contact's name.

### Viewing Message History

1. **Open a contact**
2. **Click "📋 History"**
3. View all sent emails with:
   - Status (sent, failed, draft)
   - Timestamp
   - Subject and body
   - Error messages (if failed)

## API Endpoints

### Send Email
```http
POST /messages/email/send
Content-Type: application/json

{
  "contact_id": "string",
  "email": "recipient@example.com",
  "subject": "Email subject",
  "body": "Message body",
  "is_draft": false
}
```

### Save Draft
```http
POST /messages/email/draft
Content-Type: application/json

{
  "contact_id": "string",
  "email": "recipient@example.com",
  "subject": "Email subject",
  "body": "Message body"
}
```

### Get Message History
```http
GET /messages/contact/{contact_id}
```

### Get Templates
```http
GET /messages/templates
```

### Render Template
```http
POST /messages/templates/render
Content-Type: application/json

{
  "template_name": "greeting",
  "context": {
    "contact_name": "John Doe",
    "user_name": "Your Name",
    "custom_message": "Hope you're doing well!"
  }
}
```

## Troubleshooting

### "SMTP credentials not configured"
- Make sure you set `SMTP_USERNAME` and `SMTP_PASSWORD` in `.env`
- Restart the application after updating `.env`

### "Failed to send email: Authentication failed"
- **Gmail**: Make sure you're using an App Password, not your regular password
- **Outlook**: Ensure "Less secure app access" is enabled if needed
- Verify username/password are correct

### "Connection refused" or "Timeout"
- Check your SMTP server and port settings
- Ensure your firewall allows outbound SMTP connections (port 587 or 465)
- Some networks block SMTP; try a different network or use SendGrid

### Email sent but not received
- Check recipient's spam/junk folder
- Verify sender email is valid
- For production, use SendGrid or similar service with proper SPF/DKIM setup

## Database Schema

Messages are stored in the `messages` collection:

```javascript
{
  _id: "string",              // Unique message ID
  _contact_id: "string",      // Reference to contact
  type: "email" | "sms",      // Message type
  direction: "sent" | "received",
  recipient: "string",        // Email address or phone
  subject: "string",          // Email subject (optional)
  body: "string",             // Message content
  status: "draft" | "sending" | "sent" | "failed" | "delivered",
  timestamp: "2026-02-12T...",
  delivered_at: "2026-02-12T..." (optional),
  error_message: "string" (optional),
  metadata: {
    provider: "smtp" | "sendgrid",
    message_id: "string"
  }
}
```

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use App Passwords** for Gmail (not your main password)
3. **Rotate API keys** periodically
4. **Use SendGrid for production** (better deliverability and security)
5. **Implement rate limiting** for production (prevent spam)

## Future Enhancements

- [ ] Rich text editor for email body
- [ ] Email attachments
- [ ] Scheduled emails
- [ ] Email tracking (opens, clicks)
- [ ] SMS messaging integration
- [ ] Bulk messaging to multiple contacts
- [ ] Email signature customization

## Support

For issues or questions:
1. Check the console/logs for error messages
2. Verify `.env` configuration
3. Test with a simple email first
4. Check the DESIGN.md for architecture details
