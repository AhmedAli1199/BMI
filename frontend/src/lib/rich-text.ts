/**
 * Email bodies are stored either as plain text (older templates, some with **bold** marks)
 * or as simple HTML written by the formatting editor. These helpers move between the two
 * and keep only the safe, basic formatting an email needs.
 */

const TAGS = new Set(["p", "div", "br", "b", "strong", "i", "em", "u", "s", "span", "font", "mark", "a", "ul", "ol", "li", "h1", "h2", "h3", "blockquote", "table", "tbody", "thead", "tr", "td", "th", "img", "hr"]);
const STYLES = new Set(["color", "background-color", "font-weight", "font-style", "text-decoration", "text-decoration-line", "text-align", "font-size", "font-family"]);

export function isHtml(body: string): boolean {
  return /<(p|div|br|table|span|a|b|strong|em|i|u|mark|font|ul|ol|h\d)(\s[^>]*)?\/?>/i.test(body || "");
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(s: string): string {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>");
}

/** Plain text (with optional **bold**, *italic* and "- " bullet lines) -> simple HTML. */
export function textToHtml(text: string): string {
  if (!text) return "";
  if (isHtml(text)) return text;
  const out: string[] = [];
  let list: string[] = [];
  const flush = () => { if (list.length) { out.push(`<ul>${list.map((l) => `<li>${l}</li>`).join("")}</ul>`); list = []; } };
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*[-•]\s+(.*)$/);
    if (m) { list.push(inline(m[1])); continue; }
    flush();
    out.push(line.trim() ? `<div>${inline(line)}</div>` : "<div><br></div>");
  }
  flush();
  return out.join("");
}

/** HTML -> readable plain text (for copying, card previews and letters). */
export function htmlToText(body: string): string {
  if (!isHtml(body)) return (body || "").replace(/\*\*(.+?)\*\*/g, "$1");
  if (typeof DOMParser === "undefined") return body.replace(/<br\s*\/?>|<\/(p|div|li)>/gi, "\n").replace(/<[^>]+>/g, "").trim();
  const doc = new DOMParser().parseFromString(sanitizeHtml(body), "text/html");
  doc.querySelectorAll("br").forEach((b) => b.replaceWith("\n"));
  doc.querySelectorAll("li").forEach((li) => li.prepend("- "));
  doc.querySelectorAll("p, div, li, h1, h2, h3, tr").forEach((el) => el.append("\n"));
  return (doc.body.textContent ?? "").replace(/\n{3,}/g, "\n\n").trim();
}

/** Keep only basic formatting tags, safe links and a few text styles. */
export function sanitizeHtml(html: string, opts: { dataImages?: boolean } = {}): string {
  if (typeof DOMParser === "undefined") return html.replace(/<script[\s\S]*?<\/script>/gi, "");
  const doc = new DOMParser().parseFromString(html, "text/html");
  const clean = (node: Element) => {
    for (const child of Array.from(node.children)) {
      const tag = child.tagName.toLowerCase();
      if (["script", "style", "iframe", "object", "embed", "head", "meta", "link", "form", "input", "button"].includes(tag)) { child.remove(); continue; }
      clean(child);
      if (!TAGS.has(tag)) { child.replaceWith(...Array.from(child.childNodes)); continue; }
      for (const attr of Array.from(child.attributes)) {
        const name = attr.name.toLowerCase();
        if (name === "style") {
          const kept = attr.value.split(";").map((d) => d.trim()).filter((d) => {
            const [prop, ...rest] = d.split(":");
            const val = rest.join(":").toLowerCase();
            return STYLES.has(prop?.trim().toLowerCase()) && !/url\(|expression|javascript:/.test(val);
          });
          if (kept.length) child.setAttribute("style", kept.join("; ")); else child.removeAttribute("style");
        } else if (name === "href" && tag === "a") {
          if (!/^(https?:|mailto:|tel:|\{\{)/i.test(attr.value.trim())) child.removeAttribute("href");
        } else if (name === "src" && tag === "img") {
          if (!/^https?:/i.test(attr.value.trim()) && !(opts.dataImages && /^data:image\/(png|jpe?g|gif);base64,/i.test(attr.value.trim()))) child.remove();
        } else if (!(tag === "font" && name === "color") && !["colspan", "rowspan", "alt", "width", "height", "target"].includes(name)) {
          child.removeAttribute(attr.name);
        }
      }
      if (tag === "a") { child.setAttribute("target", "_blank"); child.setAttribute("rel", "noreferrer"); }
    }
  };
  clean(doc.body);
  return doc.body.innerHTML;
}

/** The editor's output with an empty editor counted as empty. */
export function normaliseEditorHtml(html: string): string {
  const stripped = html.replace(/<br\s*\/?>|<\/?(div|p)>|&nbsp;|\s/gi, "");
  return stripped ? html : "";
}
