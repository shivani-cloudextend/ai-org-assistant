# AI Organization Assistant - React UI

A beautiful, modern React interface for the AI Organization Assistant.

## Features

### 🔄 Sync Tab
- **Select Data Sources:** Choose from GitHub, Confluence, or Jira
- **Configure Repositories:** Specify which GitHub repositories to sync
- **Confluence Spaces:** Define Confluence spaces to include
- **Path Filtering:** Include or exclude specific paths
- **Real-time Status:** Automatic polling to show sync progress
- **Live Updates:** See documents processed, chunks generated, and errors in real-time

### 💬 Query Tab
- **Role-Based Queries:** Select your role (Developer, Support, Manager, General)
- **Simple Interface:** Clean textarea for asking questions
- **Rich Responses:** Get detailed AI-generated answers with:
  - Processing time
  - Confidence scores
  - Source documents with links
  - Suggested actions
- **Keyboard Shortcut:** Press `Ctrl+Enter` to submit queries quickly

## Getting Started

### Prerequisites
- Node.js 14+ installed
- AI Organization Assistant backend running on `http://localhost:8000`

### Installation

1. Navigate to the UI directory:
```bash
cd ai-assistant-ui
```

2. Install dependencies (already done):
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Open your browser to:
```
http://localhost:3000
```

## Usage

### Syncing Data

1. Click the **"🔄 Sync Data"** tab
2. Select your data sources (GitHub, Confluence, Jira)
3. Fill in optional configuration:
   - **Repositories:** Comma-separated list (e.g., `backend-services, frontend-app`)
   - **Spaces:** Comma-separated Confluence spaces (e.g., `PRP, DOCS`)
   - **Include Paths:** One path per line
   - **Exclude Paths:** One path per line
4. Click **"🚀 Start Sync"**
5. Watch real-time progress updates!

**Example Sync:**
```
Sources: ✓ GitHub, ✓ Confluence
Repositories: backend-services
Spaces: PRP
Include Paths:
  prp/autopilot/
  src/
Exclude Paths:
  tests/
  node_modules/
```

### Querying the AI

1. Click the **"💬 Query Assistant"** tab
2. Select your user role from the dropdown
3. Type your question in the textarea
4. Click **"🚀 Ask Question"** (or press `Ctrl+Enter`)
5. View the AI-generated answer with sources!

**Example Queries:**
- "How does the NetSuite to Outlook sync work?"
- "What are the requirements for hierarchical folder creation?"
- "Why is the error 'Error creating the Onedrive Folders' thrown?"
- "Explain the AttachmentRequestBuilder class"

## API Configuration

The UI connects to the backend at `http://localhost:8000` by default.

To change the API endpoint, update the fetch URLs in:
- `src/components/SyncForm.js` (lines with `fetch('http://localhost:8000/...`)
- `src/components/QueryForm.js` (lines with `fetch('http://localhost:8000/...`)

## Technology Stack

- **React** 18.x
- **Create React App** - Zero configuration setup
- **CSS3** - Modern styling with gradients and animations
- **Fetch API** - For backend communication

## Project Structure

```
ai-assistant-ui/
├── public/
├── src/
│   ├── components/
│   │   ├── SyncForm.js       # Sync data form
│   │   ├── SyncForm.css      # Sync form styles
│   │   ├── QueryForm.js      # Query interface
│   │   └── QueryForm.css     # Query form styles
│   ├── App.js                # Main app with tabs
│   ├── App.css               # Main app styles
│   └── index.js              # React entry point
├── package.json
└── README_UI.md
```

## Features in Detail

### Sync Form
- **Checkbox selection** for multiple data sources
- **Conditional fields** - Only show relevant inputs
- **Status polling** - Automatically checks sync progress every 3 seconds
- **Visual feedback** - Color-coded status (⏳ Running, ✅ Completed, ❌ Failed)

### Query Form
- **Role selection** - Tailored responses based on user role
- **Multiline textarea** - Comfortable question input
- **Keyboard shortcut** - `Ctrl+Enter` for power users
- **Formatted answers** - Preserves line breaks and formatting
- **Source linking** - Direct links to Confluence pages and GitHub files
- **Confidence scoring** - See how confident the AI is

## Customization

### Changing Colors
Edit the gradient in `src/App.css`:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Adding More Roles
Update the role dropdown in `src/components/QueryForm.js`:
```jsx
<option value="your-role">Your Role</option>
```

## Troubleshooting

**Issue: Cannot connect to server**
- Solution: Ensure the backend is running on `http://localhost:8000`
- Check: Run `curl http://localhost:8000/health` in terminal

**Issue: Sync status not updating**
- Solution: Check browser console for errors
- Ensure the `/sync/status` endpoint is accessible

**Issue: CORS errors**
- Solution: Backend needs to allow CORS from `http://localhost:3000`
- Add CORS middleware to the FastAPI backend

## Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

To serve the production build:
```bash
npx serve -s build
```

## Contributing

Feel free to enhance the UI with:
- Dark mode toggle
- More data source options
- Advanced filtering options
- Export query results
- Query history

## Support

For issues or questions about the UI, check:
1. Browser console for errors
2. Backend server logs
3. Network tab in DevTools

Happy querying! 🚀

