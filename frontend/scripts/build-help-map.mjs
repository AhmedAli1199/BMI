/**
 * Builds the assistant's screen map (backend/app/brain/help/ui_map.json): for every page, the files it's made
 * from, and every button, link, tab, menu item and hint in them with its exact label and where it's written
 * ("components/deals/deal-actions.tsx:120" - the same as the data-src the feedback loader stamps on the page).
 * The assistant uses it to match what someone pointed at to the right guide, and to only "Show me" buttons
 * that really exist. The help-guide coverage test reads it too.
 *
 *   npm run help-map        (run after changing any screen; the output is committed)
 */
import { parse } from "@babel/parser";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SRC = path.join(ROOT, "src");
const OUT = path.resolve(ROOT, "../backend/app/brain/help/ui_map.json");
const DEPTH = 4;

const CLICKABLE = new Map([
  ["Button", "button"], ["button", "button"], ["a", "link"], ["Link", "link"], ["DropdownMenuItem", "menu item"],
  ["MenuItem", "menu item"], ["TabsTrigger", "tab"], ["SelectItem", "option"], ["SheetTitle", "panel"], ["DialogTitle", "dialog"],
  ["CardTitle", "heading"], ["h2", "heading"], ["h3", "heading"], ["legend", "heading"], ["label", "field"], ["Label", "field"], ["th", "column"],
]);

const rel = (f) => path.relative(SRC, f).split(path.sep).join("/");

function walk(node, visit, parents = []) {
  if (!node || typeof node.type !== "string") return;
  visit(node, parents);
  for (const key of Object.keys(node)) {
    if (["loc", "start", "end", "extra", "leadingComments", "trailingComments", "innerComments"].includes(key)) continue;
    const v = node[key];
    if (Array.isArray(v)) v.forEach((c) => c && typeof c === "object" && walk(c, visit, [...parents, node]));
    else if (v && typeof v === "object" && typeof v.type === "string") walk(v, visit, [...parents, node]);
  }
}

function text(node) {
  // Only words written into the code (not {variables}) - "Booking {number}" becomes "Booking …".
  let out = "";
  for (const c of node.children || []) {
    if (c.type === "JSXText") out += c.value;
    else if (c.type === "JSXExpressionContainer") {
      const e = c.expression;
      if (e.type === "StringLiteral") out += e.value;
      else if (e.type === "TemplateLiteral" && e.quasis.length === 1) out += e.quasis[0].value.cooked;
      else if (e.type === "ConditionalExpression" && e.consequent.type === "StringLiteral") out += e.consequent.value;
      else if (e.type !== "JSXEmptyExpression") out += " … ";
    } else if (c.type === "JSXElement") out += " " + text(c) + " ";
  }
  return out.replace(/&apos;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/\s+/g, " ").trim().replace(/^(…\s*)+|(\s*…)+$/g, "").trim();
}

function attr(node, name) {
  const a = node.openingElement.attributes.find((x) => x.type === "JSXAttribute" && x.name?.name === name);
  if (!a?.value) return null;
  if (a.value.type === "StringLiteral") return a.value.value;
  if (a.value.type === "JSXExpressionContainer" && a.value.expression.type === "StringLiteral") return a.value.expression.value;
  return null;
}

const cache = new Map();
function scan(file) {
  if (cache.has(file)) return cache.get(file);
  const res = { imports: [], elements: [] };
  cache.set(file, res);
  let ast;
  try { ast = parse(fs.readFileSync(file, "utf8"), { sourceType: "module", plugins: ["typescript", "jsx"] }); } catch { return res; }
  for (const n of ast.program.body) {
    if (n.type !== "ImportDeclaration") continue;
    const s = n.source.value;
    const base = s.startsWith("@/") ? path.join(SRC, s.slice(2)) : s.startsWith(".") ? path.resolve(path.dirname(file), s) : null;
    if (!base) continue;
    for (const cand of [base + ".tsx", path.join(base, "index.tsx")]) if (fs.existsSync(cand)) { res.imports.push(cand); break; }
  }
  walk(ast.program, (node) => {
    if (node.type !== "JSXElement" || node.openingElement.name.type !== "JSXIdentifier") return;
    const name = node.openingElement.name.name;
    const src = `${rel(file)}:${node.openingElement.loc.start.line}`;
    if (name === "InfoHint") {
      const hint = text(node);
      if (hint) res.elements.push({ file: rel(file), src, kind: "hint", label: "", hint });
      return;
    }
    const kind = CLICKABLE.get(name);
    if (!kind) return;
    const label = (text(node) || attr(node, "aria-label") || attr(node, "title") || "").slice(0, 120);
    if (!label || !/[a-z]{2}/i.test(label)) return;
    res.elements.push({ file: rel(file), src, kind, label });
  });
  return res;
}

function filesFor(page) {
  const seen = new Set();
  const visit = (f, d) => {
    if (seen.has(f) || d > DEPTH) return;
    // the app shell and generic ui pieces aren't part of any one screen
    if (/\/components\/(ui|data-view)\//.test(f) || /app-sidebar|feedback\/|brain\//.test(f)) return;
    seen.add(f);
    for (const i of scan(f).imports) visit(i, d + 1);
  };
  visit(page, 0);
  return [...seen].sort();
}

function pages(dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...pages(p));
    else if (e.name === "page.tsx") out.push(p);
  }
  return out;
}

const screens = [];
const used = new Set();
for (const p of pages(path.join(SRC, "app")).sort()) {
  const route = "/" + path.relative(path.join(SRC, "app"), path.dirname(p)).split(path.sep).filter((s) => !/^\(.*\)$/.test(s)).join("/");
  if (route.startsWith("/api")) continue;
  const files = filesFor(p);
  files.forEach((f) => used.add(f));
  screens.push({ route: route === "/" ? "/" : route.replace(/\/$/, ""), page: rel(p), files: files.map(rel) });
}
const elements = [...used].sort().flatMap((f) => scan(f).elements);
fs.writeFileSync(OUT, JSON.stringify({ screens, elements }, null, 1) + "\n");
console.log(`help map: ${screens.length} screens, ${elements.length} buttons, links and hints -> ${path.relative(ROOT, OUT)}`);
