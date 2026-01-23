# Troubleshooting: API.exe in Electron

## Issue: "No Assistance response..." when running api.exe in Electron

### Common Causes

1. **Environment Variables Not Passed**
   - When Electron spawns `api.exe`, it might not pass environment variables
   - Check if Electron is setting environment variables before spawning the process

2. **Response Structure Differences**
   - Azure AI response structure might differ when running in Electron context
   - The response object might not have `output_text` attribute

3. **Network/Proxy Issues**
   - Electron might have different network settings
   - Corporate proxies might block requests

4. **Working Directory Issues**
   - `.env` file might not be found if working directory is different

### Debugging Steps

1. **Check Environment Variables**
   - When `api.exe` starts, it will print environment variable status
   - Look for the debug output showing which variables are SET/NOT SET
   - Ensure Electron passes these environment variables:
     - `AZURE_AI_API_ENDPOINT`
     - `AZURE_AI_AGENT`
     - `AZURE_TENANT_ID`
     - `AZURE_CLIENT_ID`
     - `AZURE_CLIENT_SECRET`

2. **Check Debug Output**
   - The code now prints detailed debug information about:
     - Response object type and attributes
     - How response text is extracted
     - Any errors during processing
   - Look for lines starting with "DEBUG:" in the console output

3. **Verify Electron Process Spawn**
   - Ensure Electron is spawning `api.exe` with environment variables:
   ```javascript
   const { spawn } = require('child_process');
   const apiProcess = spawn('api.exe', [], {
     env: {
       ...process.env,  // Inherit parent environment
       AZURE_AI_API_ENDPOINT: 'your-endpoint',
       AZURE_AI_AGENT: 'your-agent',
       AZURE_TENANT_ID: 'your-tenant-id',
       AZURE_CLIENT_ID: 'your-client-id',
       AZURE_CLIENT_SECRET: 'your-client-secret',
     },
     cwd: pathToApiExeDirectory  // Set working directory
   });
   ```

4. **Check Log Files**
   - Check the `logs/` directory for analysis logs
   - Look for error messages in chunk logs

### Solutions

#### Solution 1: Pass Environment Variables in Electron

Make sure Electron passes all required environment variables when spawning `api.exe`:

```javascript
// In your Electron main process
const apiProcess = spawn('api.exe', [], {
  env: {
    ...process.env,
    AZURE_AI_API_ENDPOINT: process.env.AZURE_AI_API_ENDPOINT || 'your-endpoint',
    AZURE_AI_AGENT: process.env.AZURE_AI_AGENT || 'your-agent',
    AZURE_TENANT_ID: process.env.AZURE_TENANT_ID || 'your-tenant-id',
    AZURE_CLIENT_ID: process.env.AZURE_CLIENT_ID || 'your-client-id',
    AZURE_CLIENT_SECRET: process.env.AZURE_CLIENT_SECRET || 'your-client-secret',
  },
  cwd: path.dirname(pathToApiExe),
  stdio: ['ignore', 'pipe', 'pipe']  // Capture stdout/stderr for debugging
});

// Log output for debugging
apiProcess.stdout.on('data', (data) => {
  console.log(`API stdout: ${data}`);
});

apiProcess.stderr.on('data', (data) => {
  console.error(`API stderr: ${data}`);
});
```

#### Solution 2: Use .env File in Same Directory

Place a `.env` file in the same directory as `api.exe`:

```
AZURE_AI_API_ENDPOINT=your-endpoint
AZURE_AI_AGENT=your-agent
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

The `dotenv` package will automatically load this file.

#### Solution 3: Check Network/Proxy Settings

If running behind a corporate proxy, ensure:
- Proxy settings are configured correctly
- SSL certificates are trusted
- Firewall allows outbound HTTPS connections to Azure

#### Solution 4: Increase Timeout

If requests are timing out, you might need to increase timeout values in the Azure AI service.

### What the Debug Output Shows

When you run `api.exe`, you should see:

1. **On Startup:**
   ```
   ================================================================================
   Environment Variables Check (on startup):
   AZURE_AI_API_ENDPOINT: SET
   AZURE_AI_AGENT: SET
   AZURE_TENANT_ID: SET
   AZURE_CLIENT_ID: SET
   AZURE_CLIENT_SECRET: SET
   ================================================================================
   ```

2. **During Analysis:**
   ```
   DEBUG: Response object type: <class '...'>
   DEBUG: Response object attributes: [...]
   DEBUG: output_text found: True, length: 1234
   DEBUG: Final response_text length: 1234
   ```

3. **If No Response:**
   ```
   DEBUG: No response text found. Response object: ...
   DEBUG: Response str representation: ...
   DEBUG: No response text found, using fallback
   ```

### Next Steps

1. Run `api.exe` in Electron and capture all console output
2. Check which environment variables are missing (if any)
3. Check the debug output to see how the response is being parsed
4. Compare the response structure when running standalone vs in Electron
5. Share the debug output to identify the exact issue
