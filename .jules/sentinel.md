## 2025-03-01 - Mitigate user enumeration timing attack in verify_password
**Vulnerability:** User enumeration timing attack and unhandled NoneType in `verify_password`.
**Learning:** Returning early or throwing an exception when a user is not found (and hash is `None`) creates a noticeable timing difference compared to a valid login attempt. Attackers can use this to enumerate registered users.
**Prevention:** Normalize response times by executing a dummy bcrypt hash validation (`bcrypt.checkpw`) against a hardcoded dummy hash when the retrieved user hash is `None`.
