## 2026-04-04 - Improve keyboard accessibility with focus-visible
**Learning:** Custom buttons and interactive elements often lack clear focus indicators for keyboard users when relying on standard hover states. Using `:focus-visible` ensures focus rings only appear during keyboard navigation and not on mouse clicks, reducing visual noise while improving accessibility.
**Action:** Always append `:focus-visible` styles with outline and outline-offset for all custom interactive elements.
