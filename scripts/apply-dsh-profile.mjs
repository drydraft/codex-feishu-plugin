#!/usr/bin/env node
/**
 * Add or remove the dsh-feishu bundle in a DeepSeek Harness profile.
 *
 * The Harness desktop app owns its profile, so this script edits exactly the
 * two declarative places a bundle needs and nothing else:
 *   1. package.json dependencies  -> link:<absolute package directory>
 *   2. package.json dsh.profile.bundles -> bundle is applied to the tree
 *
 * It never touches cordis.patch.yml, sessions, or credentials. Every write is
 * preceded by a timestamped backup and is a no-op when the desired state is
 * already present.
 *
 * Usage:
 *   node scripts/apply-dsh-profile.mjs --profile <dir> --package <dir> [--dry-run]
 *   node scripts/apply-dsh-profile.mjs --profile <dir> --remove [--dry-run]
 */
import fs from 'node:fs';
import path from 'node:path';

const BUNDLE_NAME = 'dsh-feishu';

function fail(message, code = 2) {
  process.stderr.write(`${message}\n`);
  process.exit(code);
}

function parseArgs(argv) {
  const options = { profile: null, packageDir: null, dryRun: false, remove: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--profile') options.profile = argv[++index];
    else if (argument === '--package') options.packageDir = argv[++index];
    else if (argument === '--dry-run') options.dryRun = true;
    else if (argument === '--remove') options.remove = true;
    else if (argument === '--help' || argument === '-h') {
      process.stdout.write('node scripts/apply-dsh-profile.mjs --profile <dir> (--package <dir> | --remove) [--dry-run]\n');
      process.exit(0);
    } else fail(`Unknown argument: ${argument}`);
  }
  return options;
}

/** Express an absolute Windows path as a forward-slash link: specifier. */
function linkSpecifier(directory) {
  return `link:${path.resolve(directory).split(path.sep).join('/')}`;
}

const options = parseArgs(process.argv.slice(2));
if (!options.profile) fail('--profile <dir> is required');
if (!options.remove && !options.packageDir) fail('--package <dir> is required unless --remove is given');

const profileDirectory = path.resolve(options.profile);
const manifestPath = path.join(profileDirectory, 'package.json');
if (!fs.existsSync(manifestPath)) fail(`Profile manifest not found: ${manifestPath}`);

let manifest;
try {
  manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
} catch (error) {
  fail(`Profile manifest is not valid JSON: ${error.message}`);
}

const profileBlock = manifest.dsh?.profile;
if (!profileBlock || !Array.isArray(profileBlock.bundles)) {
  fail('Profile manifest has no dsh.profile.bundles array; refusing to guess');
}

const before = JSON.stringify(manifest);
const changes = [];

if (options.remove) {
  if (manifest.dependencies && BUNDLE_NAME in manifest.dependencies) {
    delete manifest.dependencies[BUNDLE_NAME];
    changes.push(`removed dependency ${BUNDLE_NAME}`);
  }
  const remaining = profileBlock.bundles.filter((entry) => entry !== BUNDLE_NAME);
  if (remaining.length !== profileBlock.bundles.length) {
    profileBlock.bundles = remaining;
    changes.push(`removed bundle ${BUNDLE_NAME}`);
  }
} else {
  const packageDirectory = path.resolve(options.packageDir);
  const packageManifestPath = path.join(packageDirectory, 'package.json');
  if (!fs.existsSync(packageManifestPath)) fail(`Bundle manifest not found: ${packageManifestPath}`);
  const bundle = JSON.parse(fs.readFileSync(packageManifestPath, 'utf8'));
  if (bundle.name !== BUNDLE_NAME) {
    fail(`Bundle package name is "${bundle.name}", expected "${BUNDLE_NAME}"`);
  }
  if (!bundle.dsh?.bundle?.patch) fail('Bundle manifest has no dsh.bundle.patch; refusing to install');

  manifest.dependencies ??= {};
  const specifier = linkSpecifier(packageDirectory);
  if (manifest.dependencies[BUNDLE_NAME] !== specifier) {
    manifest.dependencies[BUNDLE_NAME] = specifier;
    changes.push(`set dependency ${BUNDLE_NAME} -> ${specifier}`);
  }
  if (!profileBlock.bundles.includes(BUNDLE_NAME)) {
    profileBlock.bundles.push(BUNDLE_NAME);
    changes.push(`added bundle ${BUNDLE_NAME}`);
  }
}

const after = JSON.stringify(manifest);
const changed = before !== after;

if (options.dryRun) {
  process.stdout.write(`${JSON.stringify({ changed, dryRun: true, changes }, null, 2)}\n`);
  process.exit(0);
}

if (changed) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  fs.copyFileSync(manifestPath, `${manifestPath}.bak-dsh-feishu-${stamp}`);
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
}

process.stdout.write(`${JSON.stringify({ changed, profile: profileDirectory, changes }, null, 2)}\n`);
