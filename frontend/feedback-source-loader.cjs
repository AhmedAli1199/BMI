/**
 * Build step for the Feedback button: stamps every element written in src/ with where it comes from
 * (data-src="components/deals/deal-form.tsx:389"), so feedback that points at a button says which file
 * and line made it. Only adds an attribute; nothing else in the file changes. If a file can't be read,
 * it's left exactly as it was.
 */
const { parse } = require("@babel/parser");
const path = require("path");

const SKIP_TAGS = new Set(["html", "head", "meta", "title", "link", "script", "style", "base", "noscript"]);

function walk(node, visit) {
  if (!node || typeof node.type !== "string") return;
  visit(node);
  for (const key of Object.keys(node)) {
    if (key === "loc" || key === "start" || key === "end" || key === "extra" || key === "leadingComments" || key === "trailingComments") continue;
    const v = node[key];
    if (Array.isArray(v)) v.forEach((c) => c && typeof c === "object" && walk(c, visit));
    else if (v && typeof v === "object" && typeof v.type === "string") walk(v, visit);
  }
}

module.exports = function feedbackSourceLoader(source) {
  const file = this.resourcePath || "";
  const at = file.split(path.sep).join("/").lastIndexOf("/src/");
  if (at < 0 || file.includes("node_modules") || !/\.(tsx|jsx)$/.test(file) || !source.includes("<")) return source;
  const rel = file.split(path.sep).join("/").slice(at + 5);
  let ast;
  try {
    ast = parse(source, { sourceType: "module", plugins: ["typescript", "jsx"], errorRecovery: false });
  } catch {
    return source;
  }
  // Components from other packages may not pass the attribute on (or may complain), so leave them alone.
  const external = new Set(["Fragment"]);
  for (const n of ast.program.body) {
    if (n.type === "ImportDeclaration" && !/^(@\/|\.)/.test(n.source.value)) n.specifiers.forEach((s) => external.add(s.local.name));
  }
  const inserts = [];
  walk(ast.program, (node) => {
    if (node.type !== "JSXOpeningElement" || node.name.type !== "JSXIdentifier") return;
    const name = node.name.name;
    const intrinsic = /^[a-z]/.test(name);
    if (intrinsic ? SKIP_TAGS.has(name) : external.has(name)) return;
    if (node.attributes.some((a) => a.type === "JSXAttribute" && a.name && a.name.name === "data-src")) return;
    inserts.push([node.name.end, ` data-src="${rel}:${node.loc.start.line}"`]);
  });
  if (!inserts.length) return source;
  let out = source;
  for (const [pos, text] of inserts.sort((a, b) => b[0] - a[0])) out = out.slice(0, pos) + text + out.slice(pos);
  return out;
};
