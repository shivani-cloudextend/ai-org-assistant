# 📁 Folder Filtering Guide

The `OptimizedGitHubCollector` now supports filtering by specific folders/paths in your repositories!

## 🎯 Use Cases

1. **Only collect from specific services/modules**
2. **Exclude test directories**
3. **Focus on backend or frontend only**
4. **Skip generated code directories**

---

## 📖 How to Use

### **Option 1: Include Specific Paths Only**

Collect ONLY from specified folders:

```python
from optimized_github_collector import OptimizedGitHubCollector

collector = OptimizedGitHubCollector(
    organization="your-org",
    repositories=["backend_services"],
    include_paths=["src/api/", "src/services/"],  # ONLY these folders
    max_concurrent=10
)
```

**Result**: Only collects files from `src/api/` and `src/services/` directories.

---

### **Option 2: Exclude Specific Paths**

Collect everything EXCEPT specified folders:

```python
collector = OptimizedGitHubCollector(
    organization="your-org",
    repositories=["backend_services"],
    exclude_paths=["tests/", "examples/", "docs/"],  # EXCLUDE these
    max_concurrent=10
)
```

**Result**: Collects all files except those in `tests/`, `examples/`, or `docs/`.

---

### **Option 3: Combine Include + Exclude**

Fine-grained control:

```python
collector = OptimizedGitHubCollector(
    organization="your-org",
    repositories=["monorepo"],
    include_paths=["services/"],           # Only from services/
    exclude_paths=["services/legacy/"],    # But not legacy services
    max_concurrent=10
)
```

**Result**: Collects from `services/` but skips `services/legacy/`.

---

## 🔧 Real-World Examples

### **Example 1: Backend API Only**

```python
collector = OptimizedGitHubCollector(
    organization="acme-corp",
    repositories=["platform"],
    include_paths=[
        "backend/api/",
        "backend/services/",
        "backend/models/"
    ],
    max_concurrent=10
)
```

### **Example 2: Frontend Components Only**

```python
collector = OptimizedGitHubCollector(
    organization="acme-corp",
    repositories=["platform"],
    include_paths=[
        "frontend/src/components/",
        "frontend/src/pages/",
        "frontend/src/hooks/"
    ],
    max_concurrent=10
)
```

### **Example 3: Skip Tests and Build Artifacts**

```python
collector = OptimizedGitHubCollector(
    organization="acme-corp",
    repositories=["backend_services"],
    exclude_paths=[
        "tests/",
        "test/",
        "__tests__/",
        "build/",
        "dist/",
        ".github/"
    ],
    max_concurrent=10
)
```

### **Example 4: Specific Microservices Only**

```python
# In a microservices monorepo, only collect from auth and payment services
collector = OptimizedGitHubCollector(
    organization="acme-corp",
    repositories=["microservices"],
    include_paths=[
        "services/auth/",
        "services/payment/"
    ],
    max_concurrent=10
)
```

---

## 📋 How Paths Work

- **Paths are relative to repository root**
- **Always use forward slashes**: `src/api/` not `src\api\`
- **Include trailing slash** for directories: `src/` not `src`
- **Paths use `startswith()` matching**:
  - `"src/"` matches `src/main.py` ✅
  - `"src/"` matches `src/utils/helper.js` ✅
  - `"src/"` does NOT match `other/src/file.py` ❌

---

## 💡 Tips

### **1. Default Exclusions**

These are ALWAYS excluded (no need to specify):
- `node_modules/`
- `vendor/`
- `.git/`
- `dist/`
- `build/`
- `__pycache__/`
- `.pytest_cache/`
- `coverage/`
- `.next/`
- `target/`
- `bin/`
- `obj/`
- `.gradle/`
- `venv/`
- `env/`

### **2. Precedence**

Filtering happens in this order:
1. ✅ Check if file is a blob (not a directory)
2. ✅ Check default exclusions
3. ✅ Check `include_paths` (if specified)
4. ✅ Check `exclude_paths` (if specified)
5. ✅ Check file size
6. ✅ Check file extension

### **3. Performance**

Path filtering is **instant** - it happens locally after fetching the tree, so no additional API calls!

---

## 🚀 Using in main.py

Update your sync endpoint to support path filtering:

```python
# In main.py, modify the run_data_sync function:

github_collector = OptimizedGitHubCollector(
    organization=github_org,
    repositories=repositories,
    collect_source_code=True,
    max_file_size=100000,
    max_concurrent=10,
    include_paths=["src/", "lib/"],        # Add this
    exclude_paths=["tests/", "examples/"]  # Add this
)
```

Or make it configurable via API request:

```python
class SyncRequest(BaseModel):
    sources: List[str] = Field(default=["github"])
    repositories: Optional[List[str]] = None
    include_paths: Optional[List[str]] = None    # NEW
    exclude_paths: Optional[List[str]] = None    # NEW
```

Then use in sync:

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["backend"],
    "include_paths": ["src/api/", "src/services/"],
    "exclude_paths": ["tests/"]
  }'
```

---

## 📊 Output Example

When running with path filters, you'll see:

```
================================================================================
🚀 OPTIMIZED COLLECTION: backend_services
================================================================================

📥 Fetching repository tree structure...
✅ Got 1247 total items from repository
📁 Include paths: src/api/, src/services/
🚫 Exclude paths: tests/

✅ Found 87 source/doc files to collect

📋 File breakdown:
   .ts: 45 files
   .js: 23 files
   .json: 12 files
   .md: 7 files
```

---

## ❓ Common Questions

**Q: What if I don't specify any paths?**
A: All files are collected (subject to default exclusions and file size limits).

**Q: Can I use wildcards like `src/**/utils/`?**
A: No, only simple `startswith()` matching. Use `src/` to match everything in src.

**Q: Do I need the trailing slash?**
A: Recommended for clarity. `src/` is clearer than `src`.

**Q: How do I see which files were filtered out?**
A: Check the console output - it shows total items vs. collected files.

---

## 🎉 Benefits

- ✅ **Faster collection** - fewer files to process
- ✅ **Lower costs** - fewer API calls and embeddings
- ✅ **Better relevance** - only collect what matters
- ✅ **Cleaner results** - no test files or examples cluttering your AI responses

---

Happy filtering! 🚀

