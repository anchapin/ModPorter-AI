#!/bin/bash

# Setup script for configuring langchain-code to use Z.AI API
# This script configures langchain-code to use Z.AI's OpenAI-compatible endpoint

echo "🚀 Setting up langchain-code with Z.AI API..."

# Check if .env exists in the current directory
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create or update .env file with Z.AI configuration
cat > .env << 'EOF'
# Z.AI API Configuration for langchain-code
# These settings redirect langchain-code's OpenAI client to Z.AI's endpoint

# OpenAI Configuration (redirected to Z.AI)
OPENAI_API_KEY=your_zai_api_key_here
OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4

# Optional: Configure default model (Z.AI supports GLM-4.6, GLM-4.5, GLM-4.5-air)
OPENAI_MODEL=GLM-4.6

# Optional: Set temperature for more deterministic outputs
OPENAI_TEMPERATURE=0.1

# Additional Z.AI settings
ZAI_API_KEY=your_zai_api_key_here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4

# Other API Keys (optional - for router functionality)
# GOOGLE_API_KEY=your_google_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here
# TAVILY_API_KEY=your_tavily_key_here
EOF

echo "✅ .env file created with Z.AI configuration"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and replace 'your_zai_api_key_here' with your actual Z.AI API key"
echo "2. Get your API key from: https://docs.z.ai/devpack/tool/others"
echo "3. Run langchain-code with: langcode chat --llm openai --mode react"
echo ""
echo "🎯 Usage examples:"
echo "   langcode chat --llm openai --mode react        # Interactive chat"
echo "   langcode chat --llm openai --mode deep --auto  # Autopilot mode"
echo "   langcode feature \"Add user auth\" --llm openai"
echo "   langcode fix --llm openai"
echo "   langcode analyze --llm openai"
echo ""
echo "💡 Tip: Use GLM-4.6 for complex tasks, GLM-4.5-air for speed"