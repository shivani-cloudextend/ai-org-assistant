# 📚 Confluence Integration Setup Guide

Complete guide to collecting data from Confluence for your AI Assistant.

---

## 🔐 **Step 1: Get Confluence API Token**

### **1.1 Create an API Token**

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Give it a name (e.g., "AI Assistant")
4. Click **"Create"**
5. **Copy the token** (you won't see it again!)

### **1.2 Get Your Confluence Details**

You'll need:
- **Confluence URL**: Your Confluence site URL (e.g., `https://yourcompany.atlassian.net/wiki`)
- **Username**: Your Atlassian email address (e.g., `you@company.com`)
- **API Token**: The token you just created
- **Space Keys**: The space(s) you want to collect from (e.g., `DOCS`, `TECH`)

---

## ⚙️ **Step 2: Configure Environment Variables**

Add these to your `.env` file:

```bash
# Confluence Configuration
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-api-token-here
CONFLUENCE_SPACE_KEYS=DOCS,TECH,SUPPORT  # Comma-separated list
```

### **Finding Space Keys:**

1. Go to your Confluence space
2. Look at the URL: `https://yourcompany.atlassian.net/wiki/spaces/DOCS/...`
3. The **space key** is between `/spaces/` and the next `/` (e.g., `DOCS`)

---

## 🚀 **Step 3: Collect Confluence Data**

### **Option 1: Collect All Configured Spaces**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["confluence"]
  }'
```

This will collect from all spaces in `CONFLUENCE_SPACE_KEYS`.

---

### **Option 2: Collect Specific Spaces**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["confluence"],
    "spaces": ["DOCS", "TECH"]
  }'
```

---

### **Option 3: Collect Both GitHub + Confluence**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github", "confluence"],
    "repositories": ["backend", "frontend"],
    "spaces": ["DOCS", "TECH"]
  }'
```

---

## 📊 **What Gets Collected?**

The Confluence connector collects:

### **✅ Page Content**
- Page title
- Full page body (cleaned HTML → plain text)
- Page hierarchy (parent pages)

### **✅ Metadata**
- Page ID
- Space key
- Labels/tags
- Creator name
- Created/Updated dates
- Direct URL to page

### **✅ Smart Role Tagging**

Pages are automatically tagged based on content:

**Developer tags** (for technical pages):
- API documentation
- SDK guides
- Architecture docs
- HLD/LLD documents
- Deployment guides

**Support tags** (for user-facing pages):
- Troubleshooting guides
- FAQs
- How-to guides
- Support documentation
- Known issues

**Manager tags** (for high-level pages):
- Roadmaps
- Strategy documents
- Planning pages
- Meeting notes

---

## 🔍 **Example: What You'll See**

When syncing Confluence, you'll see:

```
INFO:main:Starting Confluence sync...
INFO:data_collectors:Starting Confluence data collection for spaces: ['DOCS', 'TECH']
INFO:data_collectors:Found 45 pages in space DOCS
INFO:data_collectors:Found 23 pages in space TECH
INFO:main:Collected 68 documents...

================================================================================
📊 COLLECTION SUMMARY
================================================================================
✅ Total documents collected: 268 (200 GitHub + 68 Confluence)

📄 Sample Confluence Documents:
--------------------------------------------------------------------------------
1. Source: confluence
   Type: documentation
   Title: API Integration Guide
   Space: TECH
   Labels: api, integration, developer
   Role Tags: developer
   Content preview: This guide explains how to integrate with our REST API...

2. Source: confluence
   Type: documentation
   Title: Troubleshooting Common Issues
   Space: DOCS
   Labels: support, troubleshooting, faq
   Role Tags: support
   Content preview: Here are solutions to common problems...
```

---

## 🛠️ **Advanced Configuration**

### **Multiple Organizations**

If you have multiple Confluence instances:

```bash
# Instance 1 (Internal)
CONFLUENCE_URL=https://internal.atlassian.net/wiki
CONFLUENCE_USERNAME=you@company.com
CONFLUENCE_API_TOKEN=token-1
CONFLUENCE_SPACE_KEYS=INTERNAL,TECH

# Instance 2 (Customer)
# You'd need to modify the code to support multiple instances
```

---

### **Filtering Pages**

Currently, the connector collects **all pages** from specified spaces. To filter:

**Option 1: By Space** (use specific space keys)
```json
{"spaces": ["DOCS"]}  // Only DOCS space
```

**Option 2: By Labels** (future enhancement)
```python
# In data_collectors.py, add label filtering:
if labels and not any(label in allowed_labels for label in page_labels):
    continue  # Skip this page
```

---

## 🚨 **Common Issues**

### **1. Authentication Error**
```
Error: 401 Unauthorized
```

**Solution:**
- Double-check your email and API token
- Make sure you copied the token correctly (no extra spaces)
- Try creating a new API token

---

### **2. Space Not Found**
```
Error processing Confluence space DOCS: Space not found
```

**Solution:**
- Check the space key is correct (case-sensitive!)
- Make sure you have access to that space
- Check the URL format is correct

---

### **3. No Pages Found**
```
Found 0 pages in space DOCS
```

**Solution:**
- The space might be empty
- You might not have read permissions
- Check space key is correct

---

### **4. HTML Parsing Issues**
```
Error processing page: [Some HTML error]
```

**Solution:**
- Some Confluence pages have complex macros
- The page will be skipped, others will continue
- Check the logs for which page failed

---

## 📈 **Performance**

- **Speed**: ~5-10 pages per second
- **Large spaces** (1000+ pages): May take several minutes
- **Rate limits**: Confluence API has rate limits (1000 requests/hour typically)

---

## 💡 **Tips**

### **1. Start Small**
Test with one small space first:
```json
{"sources": ["confluence"], "spaces": ["TEST"]}
```

### **2. Organize by Spaces**
Keep different types of docs in different spaces:
- `DEV` - Developer documentation
- `USER` - User guides
- `SUPPORT` - Support documentation

### **3. Use Labels**
Add labels to Confluence pages for better role-based retrieval:
- `developer` - Technical docs
- `support` - Support guides
- `manager` - Planning docs

### **4. Regular Syncs**
Schedule regular syncs to keep data fresh:
```bash
# Cron job: Sync every night at 2 AM
0 2 * * * curl -X POST http://localhost:8000/sync -H "Content-Type: application/json" -d '{"sources": ["confluence"]}'
```

---

## 🔄 **Full Example: Complete Setup**

### **1. Create `.env`**
```bash
# Confluence
CONFLUENCE_URL=https://acme.atlassian.net/wiki
CONFLUENCE_USERNAME=john@acme.com
CONFLUENCE_API_TOKEN=ATATTxxx...xxxxx
CONFLUENCE_SPACE_KEYS=DOCS,TECH,SUPPORT
```

### **2. Start Server**
```bash
python3 main.py
```

### **3. Sync Confluence + GitHub**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github", "confluence"],
    "repositories": ["backend"],
    "spaces": ["DOCS"]
  }'
```

### **4. Check Status**
```bash
curl http://localhost:8000/sync/status
```

### **5. Query the Data**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I troubleshoot authentication errors?",
    "user_role": "support"
  }'
```

---

## ✅ **Verification Checklist**

- [ ] API token created
- [ ] `.env` file configured
- [ ] Space keys are correct
- [ ] You have access to the spaces
- [ ] Server is running
- [ ] Test sync with one space works
- [ ] Pages appear in collection summary

---

## 🎯 **Next Steps**

Once Confluence is set up:
1. ✅ Sync data from Confluence
2. ✅ Enable embedding & storage (uncomment in `main.py`)
3. ✅ Query your combined GitHub + Confluence knowledge base
4. ✅ Get AI responses based on both code and documentation!

---

Need help? Check the logs in your terminal for detailed error messages! 🚀

