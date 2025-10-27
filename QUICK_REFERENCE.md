# 🚀 Quick Reference: Repository Filtering

## Option 1: Global Filtering (All Repos)

Apply the same filter to all repositories:

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["repo1", "repo2", "repo3"],
    "include_paths": ["src/"],
    "exclude_paths": ["tests/"]
  }'
```

**Result**: All repos collect only from `src/`, excluding `tests/`

---

## Option 2: Per-Repository Filtering

Different filters for each repository:

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["repo1", "repo2", "repo3"],
    "repo_configs": {
      "repo1": {
        "include_paths": ["src/api/"]
      },
      "repo2": {
        "exclude_paths": ["tests/", "examples/"]
      }
    }
  }'
```

**Result**:
- `repo1`: Only `src/api/`
- `repo2`: Everything except `tests/` and `examples/`
- `repo3`: Everything (no config)

---

## Option 3: Mixed (Global + Per-Repo Overrides)

Global default + specific overrides:

```bash
curl -X POST "http://localhost:8000/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["github"],
    "repositories": ["repo1", "repo2", "repo3"],
    "exclude_paths": ["tests/"],
    "repo_configs": {
      "repo1": {
        "include_paths": ["src/"]
      }
    }
  }'
```

**Result**:
- `repo1`: Only `src/` (uses repo config)
- `repo2`: Everything except `tests/` (uses global)
- `repo3`: Everything except `tests/` (uses global)

---

## 📋 Field Reference

| Field | Type | Description | Applies To |
|-------|------|-------------|------------|
| `include_paths` | `List[str]` | Only collect from these paths | Global or per-repo |
| `exclude_paths` | `List[str]` | Don't collect from these paths | Global or per-repo |
| `repo_configs` | `Dict` | Per-repository configurations | Per-repo only |

---

## 💡 Common Patterns

### Backend API Only
```json
{"include_paths": ["src/api/", "src/services/"]}
```

### Frontend Components Only
```json
{"include_paths": ["src/components/", "src/pages/"]}
```

### Skip Tests and Examples
```json
{"exclude_paths": ["tests/", "test/", "__tests__/", "examples/"]}
```

### Specific Microservices
```json
{"include_paths": ["services/auth/", "services/payment/"]}
```

---

## ✅ Best Practices

1. **Use trailing slashes**: `src/` not `src`
2. **Start broad, then narrow**: Test without filters first
3. **Check the output**: Look for `📁 Include paths` in logs
4. **Mix approaches**: Use global for most, override specific repos
5. **Document your filters**: Know why you're filtering

---

For detailed examples, see:
- `FOLDER_FILTERING_GUIDE.md` - General folder filtering
- `PER_REPO_FILTERING_EXAMPLES.md` - Per-repository examples

