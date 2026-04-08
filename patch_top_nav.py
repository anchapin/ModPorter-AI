import re

with open('frontend/src/components/TopNavigation/TopNavigation.tsx', 'r') as f:
    content = f.read()

# Add ariaLabel property to navigationLinks
content = content.replace(
    "{ to: '/settings', label: '⚙️' },",
    "{ to: '/settings', label: '⚙️', ariaLabel: 'Settings' },"
)

# Replace the Link rendering map
old_map = """          {navigationLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`top-navigation__link ${isActive(to) ? 'top-navigation__link--active' : ''}`}
            >
              {label}
            </Link>
          ))}"""

new_map = """          {navigationLinks.map(({ to, label, ariaLabel }) => (
            <Link
              key={to}
              to={to}
              className={`top-navigation__link ${isActive(to) ? 'top-navigation__link--active' : ''}`}
              aria-label={ariaLabel}
              title={ariaLabel}
            >
              {ariaLabel ? <span aria-hidden="true">{label}</span> : label}
            </Link>
          ))}"""

if old_map in content:
    content = content.replace(old_map, new_map)
else:
    print("Could not find old map block")

with open('frontend/src/components/TopNavigation/TopNavigation.tsx', 'w') as f:
    f.write(content)
print("Patched TopNavigation.tsx")
