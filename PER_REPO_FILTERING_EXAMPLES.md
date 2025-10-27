# 🎯 Per-Repository Filtering Examples

You can now specify **different path filters for each repository**!

---

## 📖 How It Works

Use the `repo_configs` field to specify custom filters per repository:

```json
{
  "sources": ["github"],
  "repositories": ["repo1", "repo2", "repo3"],
  "repo_configs": {
    "repo1": {
      "include_paths": ["src/"],
      "exclude_paths": ["tests/"]
    },
    "repo2": {
      "include_paths": ["lib/", "api/"]
    }
    // repo3 will use global settings or collect everything
  }
}
```

---

## 🎯 Real-World Examples

### **Example 1: Mix of Filtered and Unfiltered Repos**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["backend_services", "frontend", "docs"],
    "repo_configs": {
      "backend_services": {
        "include_paths": ["src/api/", "src/services/"]
      },
      "frontend": {
        "include_paths": ["src/components/", "src/pages/"]
      }
    }
  }'
```

**Result:**
- ✅ `backend_services`: Only `src/api/` and `src/services/`
- ✅ `frontend`: Only `src/components/` and `src/pages/`
- ✅ `docs`: Everything (no filter specified)

---

### **Example 2: Different Exclusions Per Repo**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["monorepo", "legacy_app", "new_service"],
    "repo_configs": {
      "monorepo": {
        "exclude_paths": ["services/deprecated/", "old_modules/"]
      },
      "legacy_app": {
        "exclude_paths": ["tests/", "examples/", "docs/"]
      }
    }
  }'
```

**Result:**
- ✅ `monorepo`: Everything except `services/deprecated/` and `old_modules/`
- ✅ `legacy_app`: Everything except `tests/`, `examples/`, `docs/`
- ✅ `new_service`: Everything (no exclusions)

---

### **Example 3: Microservices - Select Specific Services**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["microservices"],
    "repo_configs": {
      "microservices": {
        "include_paths": [
          "services/auth/",
          "services/payment/",
          "services/notification/"
        ]
      }
    }
  }'
```

**Result:**
- ✅ Only collects from 3 specific services
- ❌ Ignores all other services in the monorepo

---

### **Example 4: Global + Per-Repo Overrides**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["api", "worker", "admin"],
    "exclude_paths": ["tests/", "examples/"],
    "repo_configs": {
      "admin": {
        "include_paths": ["src/"],
        "exclude_paths": ["src/legacy/"]
      }
    }
  }'
```

**Result:**
- ✅ `api`: Everything except `tests/` and `examples/` (uses global)
- ✅ `worker`: Everything except `tests/` and `examples/` (uses global)
- ✅ `admin`: Only `src/` but excluding `src/legacy/` (uses repo-specific)

---

### **Example 5: Complex Multi-Repo Setup**

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": [
      "platform-backend",
      "platform-frontend",
      "mobile-app",
      "shared-utils"
    ],
    "repo_configs": {
      "platform-backend": {
        "include_paths": ["src/api/", "src/services/", "src/models/"],
        "exclude_paths": ["src/api/v1/deprecated/"]
      },
      "platform-frontend": {
        "include_paths": ["src/components/", "src/hooks/", "src/utils/"],
        "exclude_paths": ["src/components/old/"]
      },
      "mobile-app": {
        "include_paths": ["app/screens/", "app/components/"]
      }
    }
  }'
```

**Result:**
- ✅ `platform-backend`: Specific API/services folders, excluding deprecated
- ✅ `platform-frontend`: React components/hooks/utils, excluding old components
- ✅ `mobile-app`: Only screens and components
- ✅ `shared-utils`: Everything (no config specified)

---

## 💡 Use Cases

### **1. Large Monorepo with Many Services**
```json
{
  "repositories": ["monorepo"],
  "repo_configs": {
    "monorepo": {
      "include_paths": ["services/core/", "services/api-gateway/"],
      "exclude_paths": ["services/*/tests/"]
    }
  }
}
```

### **2. Different Teams, Different Needs**
```json
{
  "repositories": ["backend", "frontend", "ml-models"],
  "repo_configs": {
    "backend": {
      "include_paths": ["src/"]
    },
    "frontend": {
      "include_paths": ["src/components/", "src/pages/"]
    },
    "ml-models": {
      "include_paths": ["models/", "training/"],
      "exclude_paths": ["training/experiments/"]
    }
  }
}
```

### **3. Legacy Code Exclusion**
```json
{
  "repositories": ["main-app", "legacy-services"],
  "repo_configs": {
    "main-app": {},  // Collect everything
    "legacy-services": {
      "exclude_paths": ["v1/", "deprecated/", "old-api/"]
    }
  }
}
```

---

## 🔄 Fallback Behavior

**Priority order:**
1. **Repo-specific config** (if provided in `repo_configs`)
2. **Global config** (if provided in `include_paths`/`exclude_paths`)
3. **Collect everything** (if neither is specified)

---

## 📊 Example Output

When you run with per-repo configs, you'll see:

```
================================================================================
🚀 OPTIMIZED COLLECTION: backend_services
================================================================================
📥 Fetching repository tree structure...
✅ Got 1247 total items from repository
📁 Include paths: src/api/, src/services/
✅ Found 87 source/doc files to collect
...

================================================================================
🚀 OPTIMIZED COLLECTION: frontend
================================================================================
📥 Fetching repository tree structure...
✅ Got 543 total items from repository
📁 Include paths: src/components/, src/pages/
✅ Found 45 source/doc files to collect
...
```

---

## 🚀 Python SDK Example

```python
import requests

# Sync with per-repository configs
response = requests.post(
    "http://localhost:8000/sync",
    json={
        "sources": ["github"],
        "repositories": ["backend", "frontend", "mobile"],
        "repo_configs": {
            "backend": {
                "include_paths": ["src/api/", "src/services/"]
            },
            "frontend": {
                "include_paths": ["src/components/"],
                "exclude_paths": ["src/components/legacy/"]
            },
            "mobile": {
                "include_paths": ["app/"]
            }
        }
    }
)

print(response.json())
```

---

## ⚠️ Important Notes

1. **Repository names must match exactly** - use the same names as in GitHub
2. **Paths are case-sensitive**
3. **Always use forward slashes** (`/`) even on Windows
4. **Include trailing slash for directories**: `src/` not `src`
5. **Empty config `{}` means collect everything** from that repo

---

## ✅ Benefits

- 🎯 **Precision**: Collect exactly what you need from each repo
- ⚡ **Performance**: Skip unnecessary files, faster collection
- 💰 **Cost**: Fewer files = fewer embeddings = lower OpenAI costs
- 🎨 **Flexibility**: Mix filtered and unfiltered repos as needed
- 📊 **Better Results**: More relevant data = better AI responses

---

Happy filtering! 🚀

