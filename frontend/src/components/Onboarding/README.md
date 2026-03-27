# Onboarding Component

Interactive onboarding flow for new ModPorter AI users.

## Features

- 6-step guided tour
- Welcome animation with Java → Bedrock conversion visualization
- Upload instructions with demo
- Feature showcase (items, blocks, entities, recipes)
- Process explanation (analyze → translate → convert → package)
- Results preview with success rate
- First conversion checklist
- Progress tracking
- LocalStorage persistence
- Responsive design

## Usage

```tsx
import { OnboardingFlow } from './components/Onboarding';

function App() {
  const [showOnboarding, setShowOnboarding] = useState(true);

  return (
    <>
      <OnboardingFlow
        isOpen={showOnboarding}
        onComplete={() => setShowOnboarding(false)}
        onClose={() => setShowOnboarding(false)}
      />
      {/* Rest of app */}
    </>
  );
}
```

## Props

- `isOpen`: boolean - Whether the onboarding is visible
- `onComplete`: () => void - Callback when all steps completed
- `onClose`: () => void - Callback when user closes/skips

## Customization

Edit `onboardingSteps` array in `OnboardingFlow.tsx` to:
- Add/remove steps
- Change content
- Modify checklist items
- Update action buttons

## State Management

Onboarding completion is stored in localStorage:
```javascript
localStorage.setItem('onboarding_completed', 'true');
```

To reset onboarding (for testing):
```javascript
localStorage.removeItem('onboarding_completed');
```
