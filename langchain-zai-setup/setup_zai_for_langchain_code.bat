@echo off
REM Setup script for configuring langchain-code to use Z.AI API on Windows

echo 🚀 Setting up langchain-code with Z.AI API...

REM Check if .env exists
if exist ".env" (
    echo ⚠️  .env file already exists. Backing up to .env.backup
    copy .env .env.backup >nul
)

REM Create .env file with Z.AI configuration
(
echo # Z.AI API Configuration for langchain-code
echo # These settings redirect langchain-code's OpenAI client to Z.AI's endpoint
echo.
echo # OpenAI Configuration ^(redirected to Z.AI^)
echo OPENAI_API_KEY=your_zai_api_key_here
echo OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
echo.
echo # Optional: Configure default model ^(Z.AI supports GLM-4.6, GLM-4.5, GLM-4.5-air^)
echo OPENAI_MODEL=GLM-4.6
echo.
echo # Optional: Set temperature for more deterministic outputs
echo OPENAI_TEMPERATURE=0.1
echo.
echo # Additional Z.AI settings
echo ZAI_API_KEY=your_zai_api_key_here
echo ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
echo.
echo # Other API Keys ^(optional - for router functionality^)
echo # GOOGLE_API_KEY=your_google_key_here
echo # ANTHROPIC_API_KEY=your_anthropic_key_here
echo # TAVILY_API_KEY=your_tavily_key_here
) > .env

echo ✅ .env file created with Z.AI configuration
echo.
echo 📝 Next steps:
echo 1. Edit .env file and replace 'your_zai_api_key_here' with your actual Z.AI API key
echo 2. Get your API key from: https://docs.z.ai/devpack/tool/others
echo 3. Run langchain-code with: langcode chat --llm openai --mode react
echo.
echo 🎯 Usage examples:
echo    langcode chat --llm openai --mode react        # Interactive chat
echo    langcode chat --llm openai --mode deep --auto  # Autopilot mode
echo    langcode feature "Add user auth" --llm openai
echo    langcode fix --llm openai
echo    langcode analyze --llm openai
echo.
echo 💡 Tip: Use GLM-4.6 for complex tasks, GLM-4.5-air for speed
pause