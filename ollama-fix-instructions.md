# Fix for Ollama Installation

## Problem
Backend integration tests fail when Ollama cannot download llama3.2 model due to network issues.

## Solution
Replace the Install Ollama section in .github/workflows/ci.yml (lines ~286-307) with:

    # Install Ollama for AI model testing
    - name: Install Ollama
      run: |
        echo "🤖 Installing Ollama with retry logic..."
        curl -fsSL https://ollama.com/install.sh | sh
        
        # Install and start Ollama service
        ollama serve &
        
        # Wait for Ollama to start
        sleep 15
        
        # Pull model with retry logic
        echo "📥 Pulling llama3.2 model with retry logic..."
        MAX_RETRIES=3
        RETRY_DELAY=30
        MODEL_PULLED=false
        
        for i in ; do
          echo "Attempt  of  to pull llama3.2..."
          
          # Use timeout and background process with longer timeout (20 minutes)
          timeout 1200 ollama pull llama3.2 &&
          {
            echo "✅ Model pull successful!"
            MODEL_PULLED=true
            break
          } ||
          {
            echo "❌ Model pull failed (attempt )"
            if [  -eq  ]; then
              echo "🚨 All retry attempts failed"
              echo "⚠️ Continuing without llama3.2 model - tests will skip model-dependent features"
              break
            fi
            echo "⏳ Waiting  seconds before retry..."
            sleep 
          }
        done
        
        # Verify installation
        echo "Final Ollama status:"
        ollama list || echo "⚠️ Cannot list models - model may not be available"
        
        # Export variable for tests to check model availability
        if [ "" = "true" ]; then
          echo "MODEL_AVAILABLE=true" >> 
        else
          echo "MODEL_AVAILABLE=false" >> 
        fi

## Key Improvements
1. **Retry Logic**: 3 attempts with 30-second delays
2. **Extended Timeout**: 20 minutes per attempt (vs default timeout)
3. **Graceful Failure**: Continue workflow even if model download fails
4. **Environment Variable**: Set MODEL_AVAILABLE for tests to check
5. **Better Logging**: Clear status messages for debugging

## Result
Tests will run to completion even if Ollama model download fails, fixing the CI issue.
