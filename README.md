# ModPorter AI

An AI-powered tool for converting Minecraft Java Edition mods to Bedrock Edition add-ons.

[![codecov](https://codecov.io/gh/anchapin/ModPorter-AI/branch/main/graph/badge.svg)](https://codecov.io/gh/anchapin/ModPorter-AI)

## 🎯 Vision
Empower Minecraft players and creators with a "one-click" AI-powered tool that intelligently converts Java Edition mods into functional Bedrock Edition add-ons using smart assumptions to bridge technical gaps.

## 🚀 Features
- **One-Click Conversion**: Upload Java mods and get Bedrock add-ons automatically
- **AI-Powered Analysis**: Multi-agent system using CrewAI for intelligent conversion
- **Smart Assumptions**: Handles incompatible features with logical workarounds
- **Detailed Reporting**: Transparent conversion reports showing all changes
- **Validation System**: AI-powered comparison between original and converted mods

## 🛠️ Tech Stack
- **Frontend**: React + TypeScript
- **Backend**: Python + FastAPI
- **AI Engine**: CrewAI + LangChain
- **Local Agent**: Node.js for Minecraft integration

## 📦 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Docker (optional)

### Development Setup
1. Clone the repository
2. Install dependencies: `npm run install-all`
3. Start development servers: `npm run dev`
4. Open http://localhost:3000

### Docker Setup
```bash
docker-compose up -d
```

## Testing

### Run all tests
npm run test

### Backend tests
cd backend && pytest

### Frontend tests
cd frontend && npm test

## 📖 Documentation

- [Product Requirements Document](docs/PRD.md)
- [API Documentation](docs/API.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

Users are responsible for ensuring they have the right to convert mods. Respect original mod licenses and Minecraft's terms of service.