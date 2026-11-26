// Writes static/js/<name>.min.js, an obfuscated copy of each script, for the browser:
//   node scripts/obfuscate.mjs
// Renamed, string-encoded, compacted code, while the .js files stay readable in the repo.
// It hides how the code reads, not what it does. Each copy starts with the SHA-1 of its
// source; script_url() (app.py) only serves it while that still matches, so an edited
// script is never shadowed by an old copy. The settings keep to the Content-Security-Policy
// (nothing evaluated) and keep global names, which the pages call.
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';

const OPTIONS = [
    '--compact true', '--identifier-names-generator hexadecimal', '--rename-globals false',
    '--string-array true', '--string-array-encoding base64', '--string-array-threshold 0.75',
    '--split-strings false', '--control-flow-flattening false', '--dead-code-injection false',
    '--self-defending false', '--debug-protection false', '--disable-console-output false',
    '--transform-object-keys false', '--unicode-escape-sequence false',
].join(' ');

for (const name of readdirSync('static/js').filter(f => f.endsWith('.js') && !f.endsWith('.min.js'))) {
    const source = `static/js/${name}`;
    const target = source.replace(/\.js$/, '.min.js');
    const temp = source.replace(/\.js$/, '.obfuscating.js');
    // Line endings normalised, so a checkout with CRLF or LF gives the same hash
    const hash = createHash('sha1').update(readFileSync(source, 'utf8').replace(/\r\n/g, '\n')).digest('hex');
    execSync(`npx --yes javascript-obfuscator@4.1.1 ${source} --output ${temp} ${OPTIONS}`, { stdio: 'pipe' });
    const code = readFileSync(temp, 'utf8');
    unlinkSync(temp);
    writeFileSync(target, `/*! source sha1:${hash} */\n${code}`);
    console.log(`${target}: ${code.length} bytes`);
}
