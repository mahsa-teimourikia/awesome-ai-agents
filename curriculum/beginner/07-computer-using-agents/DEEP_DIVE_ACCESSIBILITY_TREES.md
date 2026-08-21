# Deep Dive: Accessibility Trees (AXTrees) & Web Automation

When building a Computer-Using Agent to navigate the web, the obvious approach is to feed the LLM the raw HTML DOM. 

*The Agent fetches `google.com`, reads the HTML, finds the `<input>` tag, and types a query.*

In practice, **this fails catastrophically.**

---

## 1. The Problem with the Raw DOM

Modern web applications are not simple HTML documents. They are massive, dynamic JavaScript applications (React, Vue, Angular).
- **Token Bloat:** A standard webpage's DOM can easily exceed 100,000 tokens. Sending this to an LLM for every single click is prohibitively expensive and causes severe latency.
- **Invisible Elements:** The DOM contains thousands of `<div>` and `<script>` tags that have no visual representation to the user. The LLM gets confused trying to interact with layout wrappers instead of actual buttons.
- **Shadow DOM:** Many modern components hide their internals inside Shadow DOMs, which raw HTML parsers cannot easily traverse.

---

## 2. The SOTA Solution: Accessibility Trees (AXTree)

Instead of the DOM, SOTA Web Agents (like Skyvern or custom Playwright wrappers) use the **Accessibility Tree**.

Browsers inherently generate an AXTree to assist screen readers for visually impaired users. This tree strips away all the visual styling (CSS), layout wrappers (`<div>`), and scripts, leaving only the semantic, interactive elements (Buttons, Links, Textboxes).

### DOM vs AXTree Example

**Raw DOM (Bloated):**
```html
<div class="flex-container mb-4">
  <span class="wrapper-icon hidden"></span>
  <div class="btn-group">
    <button id="submit-btn" class="bg-blue-500 text-white rounded">
      Submit Form
    </button>
  </div>
</div>
```

**AXTree (Clean & Semantic):**
```text
[Button] "Submit Form" (id: submit-btn)
```

By feeding the AXTree to the LLM, you reduce the context window from 100,000 tokens to ~2,000 tokens. The LLM simply replies: `click(id="submit-btn")`.

---

## 3. Implementation Patterns (Playwright)

To build an AXTree agent, you utilize headless browser automation frameworks like **Playwright** or **Puppeteer**.

1. **The Wrapper:** The Python script uses Playwright to navigate to a URL.
2. **The Snapshot:** The script injects JavaScript into the page to extract the AXTree, assigning a unique, temporary integer ID to every interactive element.
3. **The Prompt:** The LLM receives the simplified tree: `[12]: Link 'Login', [13]: Button 'Sign Up'`.
4. **The Action:** The LLM outputs `click(12)`.
5. **The Execution:** Playwright maps ID `12` back to the specific DOM element and fires a native click event.

---

## 4. Limitations of AXTrees

While AXTrees are the standard for web automation, they have significant flaws:
- **Canvas/WebGL:** If a webpage uses a `<canvas>` element (e.g., Google Maps, Figma, or browser games), the AXTree is completely blind. It just sees a single blank canvas.
- **Bad Developers:** If a frontend developer builds a button using `<div onClick="...">` instead of a semantic `<button>` tag, the browser might not classify it as interactive, and it will be stripped from the AXTree, making it invisible to the Agent.

To solve these limitations, the industry is moving toward **Visual/Multimodal Agents** (OmniParser, Claude Computer Use) that actually look at screenshots rather than reading code.
