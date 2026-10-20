/**
 * dsh-feishu — Feishu/Lark workflow routing for DeepSeek Harness.
 *
 * The bundle ships two routing skills and nothing else. Every business
 * operation is performed by the installed official `lark-cli` and the
 * `lark-*` skills embedded in that binary, so the plugin never vendors
 * Feishu API surface, never stores credentials, and never guesses a
 * command that the current runtime does not advertise.
 *
 * Registration goes through the host `skills` service, which renders each
 * skill's routing fields into the session catalog and loads the body on
 * demand when the model or the user selects it.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ID = 'dsh-feishu';
const SKILL_NAMES = Object.freeze(['feishu-workflow-router', 'feishu-setup']);
const KEBAB_CASE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const BOOLEAN_LITERALS = new Map([
  ['true', true], ['yes', true], ['on', true], ['1', true],
  ['false', false], ['no', false], ['off', false], ['0', false],
]);

/** Strip one layer of matching quotes from a frontmatter scalar. */
function scalar(value) {
  const text = value.trim();
  if (text.length >= 2) {
    const first = text[0];
    const last = text.at(-1);
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return text.slice(1, -1);
    }
  }
  return text;
}

/** Read a strict boolean frontmatter value; an unknown spelling is an error. */
function booleanField(fields, key, fallback) {
  const raw = fields.get(key);
  if (raw === undefined) return fallback;
  const parsed = BOOLEAN_LITERALS.get(raw.toLowerCase());
  if (parsed === undefined) {
    throw new Error(`${PLUGIN_ID}: ${key} must be a boolean, received "${raw}"`);
  }
  return parsed;
}

/**
 * Parse the flat frontmatter subset used by bundled skills. Nested mappings
 * (for example `metadata:`) are ignored because the catalog does not use them.
 */
function parseFrontmatter(text, file) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n+([\s\S]+)$/.exec(text);
  if (!match) throw new Error(`${PLUGIN_ID}: ${file} requires frontmatter and instructions`);
  const fields = new Map();
  for (const line of match[1].split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue;
    if (/^\s/.test(line)) continue; // nested mapping such as `metadata:`
    const field = /^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$/.exec(line);
    if (!field) continue;
    const [, key, rawValue] = field;
    if (rawValue === '') continue; // mapping/keyless value; not a scalar field
    fields.set(key, scalar(rawValue));
  }
  return { fields, content: match[2].trim() };
}

/** Load and validate one bundled skill directory. */
function loadSkill(name) {
  if (!KEBAB_CASE.test(name)) throw new Error(`${PLUGIN_ID}: invalid skill name "${name}"`);
  const directory = path.join(HERE, 'skills', name);
  const file = path.join(directory, 'SKILL.md');
  const { fields, content } = parseFrontmatter(fs.readFileSync(file, 'utf8'), file);
  const declaredName = fields.get('name');
  const description = fields.get('description');
  if (declaredName !== name) {
    throw new Error(`${PLUGIN_ID}: ${file} declares name "${declaredName}" but lives in "${name}"`);
  }
  if (!description?.trim()) throw new Error(`${PLUGIN_ID}: ${file} requires a description`);
  if (!content) throw new Error(`${PLUGIN_ID}: ${file} requires instruction content`);
  return {
    name,
    description: description.trim(),
    source: 'bundled',
    path: file,
    resourceBase: { kind: 'directory', path: directory },
    invocation: {
      // Unlike the Codex build, the Harness catalog is model-driven: routing
      // guidance is useless if the model cannot select it.
      modelInvocable: booleanField(fields, 'disable-model-invocation', false) === false,
      userInvocable: booleanField(fields, 'user-invocable', true),
    },
    content,
  };
}

function loadSkills() {
  const skills = SKILL_NAMES.map(loadSkill);
  const names = new Set(skills.map((skill) => skill.name));
  if (names.size !== skills.length) throw new Error(`${PLUGIN_ID}: duplicate bundled skill name`);
  return skills;
}

/** The registry must hand back a disposer we can actually unwind. */
function requireDisposer(value, name) {
  if (typeof value !== 'function') {
    throw new Error(`${PLUGIN_ID}: skills.register("${name}") must return a disposer`);
  }
  return value;
}

/**
 * Register the bundled routing skills on the host skill registry.
 * @param {object} ctx Cordis context with the optional `skills` service.
 * @returns {function} Disposer that removes every registration made here.
 */
export function apply(ctx, config = {}) {
  const skills = loadSkills();
  const disabled = config?.enabled === false;
  if (disabled) return () => {};

  const fiber = ctx.inject(['skills'], (scope) => {
    const service = scope.get('skills');
    if (typeof service?.register !== 'function') {
      throw new Error(`${PLUGIN_ID}: host skills service does not expose register()`);
    }
    const removes = [];
    try {
      for (const skill of skills) removes.push(requireDisposer(service.register(skill), skill.name));
    } catch (error) {
      for (const remove of removes.reverse()) remove();
      throw error;
    }
    return () => {
      for (const remove of removes.reverse()) remove();
    };
  });

  return () => {
    if (fiber && typeof fiber.dispose === 'function') fiber.dispose();
    else if (typeof fiber === 'function') fiber();
  };
}

export const name = PLUGIN_ID;
