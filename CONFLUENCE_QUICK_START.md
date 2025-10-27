# ⚡ Confluence Quick Start

Get Confluence data in 5 minutes!

---

## 1️⃣ **Get API Token** (2 min)

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"**
3. Copy the token

---

## 2️⃣ **Add to `.env`** (1 min)

```bash
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_USERNAME=you@company.com
CONFLUENCE_API_TOKEN=your-token-here
CONFLUENCE_SPACE_KEYS=DOCS,TECH
```

**Finding Space Keys:**
- Go to your Confluence space
- URL looks like: `/wiki/spaces/DOCS/...`
- Space key is `DOCS`

---

## 3️⃣ **Sync Data** (2 min)

```bash
# Start server (if not running)
python3 main.py

# In another terminal:
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{"sources": ["confluence"]}'
```

---

## ✅ **Done!**

Check status:
```bash
curl http://localhost:8000/sync/status
```

---

## 🚀 **Common Use Cases**

### **Specific Spaces Only**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["confluence"],
    "spaces": ["DOCS"]
  }'
```

### **GitHub + Confluence Together**
```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github", "confluence"],
    "repositories": ["backend"],
    "spaces": ["DOCS", "TECH"]
  }'
```

---

## 🆘 **Troubleshooting**

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check email & API token in `.env` |
| Space not found | Verify space key (case-sensitive!) |
| No pages found | Check you have access to the space |

---

For detailed info, see **`CONFLUENCE_SETUP_GUIDE.md`** 📚

