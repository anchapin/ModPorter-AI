## 2024-05-18 - [Insecure Deserialization in Caching]
**Vulnerability:** Insecure deserialization using `pickle.load` in `ai-engine/utils/conversion_cache.py`.
**Learning:** The caching mechanism was using `pickle` which allows arbitrary code execution if a malicious payload is supplied. This was present in a performance optimization utility intended to cache conversion results.
**Prevention:** Use safer serialization formats like `json` instead of `pickle` when the cache is loaded from disk. Also, ensure file read/write modes are set appropriately for text files.
## 2024-05-18 - [DOM-based XSS in Mermaid diagrams]
**Vulnerability:** The `MermaidDiagram` component was using `chartRef.current.innerHTML = chart;` along with `securityLevel: 'loose'`, exposing the application to DOM-based XSS when rendering user-provided Mermaid diagrams.
**Learning:** Raw text strings were passed directly into the DOM instead of assigning them as text content. Mermaid can execute malicious scripts if not configured properly.
**Prevention:** To prevent DOM-based XSS vulnerabilities when passing raw text strings to client-side charting libraries (e.g., `mermaid.init()`), assign the string using `element.textContent = chart` rather than `element.innerHTML`, avoiding the need for heavy external sanitization libraries like `DOMPurify`. Additionally, use strict security configurations where available.
