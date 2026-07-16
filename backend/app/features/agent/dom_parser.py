"""
AutoWebAgent - Page-Agent DOM Parser (Alibaba Page-Agent Approach)
==================================================================
Serializes the live DOM into a structured, indexed text representation
that LLMs can understand — without relying on fragile CSS selectors.

Inspired by Alibaba's page-agent "DOM dehydration" technique:
https://github.com/alibaba/page-agent

The idea: instead of pre-planning selectors, we give the LLM a clean
numbered list of every interactive element on the current page. The LLM
then says "use element [3]" and we resolve that index back to the real
DOM node via XPath and interact with it via Playwright.
"""

import asyncio
from typing import Optional, Dict, Any, List
from loguru import logger


# ── JavaScript that runs INSIDE the browser to build the element tree ──────────

_DOM_SERIALIZER_JS = """
() => {
    // Only include elements the user can interact with
    const INTERACTIVE_TAGS = ['a', 'button', 'input', 'select', 'textarea',
                               'label', 'form', '[role="button"]', '[role="link"]',
                               '[role="checkbox"]', '[role="radio"]', '[role="combobox"]',
                               '[role="textbox"]', '[role="menuitem"]', '[role="tab"]',
                               '[tabindex]'];
    
    const IGNORE_ATTRS = ['class', 'style', 'data-reactid', 'data-ember-action'];
    
    const elements = document.querySelectorAll(
        'a[href], button, input:not([type="hidden"]), select, textarea, ' +
        '[role="button"], [role="link"], [role="checkbox"], [role="radio"], ' +
        '[role="combobox"], [role="textbox"], [role="menuitem"], [role="tab"], ' +
        '[tabindex]:not([tabindex="-1"])'
    );
    
    const result = [];
    let idx = 1;
    
    // Collect only visible elements
    for (const el of elements) {
        // Skip hidden elements
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || 
            style.opacity === '0' || el.offsetWidth === 0 || el.offsetHeight === 0) {
            continue;
        }
        
        // Skip off-screen elements  
        const rect = el.getBoundingClientRect();
        if (rect.top > window.innerHeight * 3 || rect.bottom < -window.innerHeight) {
            continue;
        }
        
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type') || '';
        const role = el.getAttribute('role') || '';
        const id = el.id || '';
        const name = el.getAttribute('name') || '';
        const placeholder = el.getAttribute('placeholder') || '';
        const ariaLabel = el.getAttribute('aria-label') || '';
        const ariaDescribedBy = el.getAttribute('aria-describedby') || '';
        const autocomplete = el.getAttribute('autocomplete') || '';
        const value = el.value || '';
        const text = (el.innerText || el.textContent || '').trim().substring(0, 100);
        const href = el.getAttribute('href') || '';
        
        // Build a human-readable description
        let description = tag;
        if (type) description += `[${type}]`;
        if (role) description += `(role:${role})`;
        
        // Label: best available
        let label = ariaLabel || placeholder || text || name || href;
        if (!label && ariaDescribedBy) {
            const descEl = document.getElementById(ariaDescribedBy.split(' ')[0]);
            if (descEl) label = (descEl.innerText || '').trim().substring(0, 60);
        }
        if (!label && id) label = `#${id}`;
        if (autocomplete) label += ` [autocomplete:${autocomplete}]`;
        
        // Build the XPath to target this element from Playwright
        // We use a unique index-based XPath using the element's tag + position in DOM
        function getXPath(element) {
            if (element.id) return `//*[@id='${element.id}']`;
            const parts = [];
            while (element && element.nodeType === Node.ELEMENT_NODE) {
                let count = 1;
                let sibling = element.previousSibling;
                while (sibling) {
                    if (sibling.nodeType === Node.ELEMENT_NODE && 
                        sibling.tagName === element.tagName) {
                        count++;
                    }
                    sibling = sibling.previousSibling;
                }
                parts.unshift(`${element.tagName.toLowerCase()}[${count}]`);
                element = element.parentNode;
            }
            return '/' + parts.join('/');
        }
        
        const xpath = getXPath(el);
        
        result.push({
            index: idx,
            tag: tag,
            type: type,
            role: role,
            label: label,
            description: description,
            xpath: xpath,
            id: id,
            name: name,
            autocomplete: autocomplete,
            value: value,
            text: text,
            placeholder: placeholder
        });
        
        idx++;
    }
    
    return result;
}
"""


class PageAgentDOMParser:
    """
    Serializes the live browser DOM into an indexed text tree,
    similar to Alibaba's page-agent "DOM dehydration" technique.
    
    This allows the LLM to pick elements by index number instead of
    requiring brittle CSS selectors.
    """
    
    @staticmethod
    async def get_interactive_elements(page) -> List[Dict[str, Any]]:
        """
        Execute DOM serializer inside the browser and return a list of
        interactive elements with their index, description, and XPath.
        
        Returns:
            List of element dicts with: index, tag, type, label, description, xpath
        """
        try:
            elements = await asyncio.wait_for(
                page.evaluate(_DOM_SERIALIZER_JS),
                timeout=10.0
            )
            logger.debug(f"🔍 DOM Parser found {len(elements)} interactive elements")
            return elements or []
        except asyncio.TimeoutError:
            logger.warning("⏱ DOM Parser timed out after 10s")
            return []
        except Exception as e:
            logger.warning(f"⚠️ DOM Parser error: {e}")
            return []
    
    @staticmethod
    def serialize_to_text(elements: List[Dict[str, Any]]) -> str:
        """
        Convert the element list into a clean text format for the LLM.
        
        Output format:
            [1] input[email] "Email or phone" (autocomplete:username)
            [2] input[password] "Password" (autocomplete:current-password)
            [3] button "Sign in"
            [4] a "Forgot password?" → /forgot-password
        """
        lines = []
        for el in elements:
            idx = el['index']
            desc = el['description']
            label = el.get('label', '').strip()
            
            # Format the line
            label_str = f' "{label}"' if label else ''
            
            # Add extra hints for common patterns
            extras = []
            if el.get('autocomplete'):
                extras.append(f"autocomplete:{el['autocomplete']}")
            if el.get('value'):
                extras.append(f"value:{str(el['value'])[:30]}")
            
            extra_str = f" ({', '.join(extras)})" if extras else ""
            lines.append(f"[{idx}] {desc}{label_str}{extra_str}")
        
        return "\n".join(lines) if lines else "(no interactive elements found)"
    
    @staticmethod
    async def get_element_by_index(page, index: int, elements: List[Dict[str, Any]]):
        """
        Resolve a DOM element index back to a Playwright locator.
        
        Uses the XPath stored during serialization to target the exact element.
        Returns a Playwright element handle.
        """
        target = next((el for el in elements if el['index'] == index), None)
        if not target:
            raise ValueError(f"Element index [{index}] not found in DOM tree")
        
        xpath = target['xpath']
        logger.debug(f"🎯 Resolving element [{index}]: {target['description']} via xpath={xpath}")
        
        # Use XPath locator
        locator = page.locator(f"xpath={xpath}").first
        
        # Verify element is visible
        try:
            await locator.wait_for(state="visible", timeout=5000)
        except Exception:
            # Fallback: try by type and autocomplete  
            if target.get('autocomplete'):
                locator = page.locator(f"[autocomplete='{target['autocomplete']}']").first
            elif target.get('type'):
                locator = page.locator(f"input[type='{target['type']}']").first
        
        return locator
